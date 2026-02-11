package com.spectra.aqc.service;

import com.spectra.aqc.model.QualityControlJob;
import com.spectra.aqc.repository.JobRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

@Service
@RequiredArgsConstructor
public class QualityControlService {

    private final FileStorageService fileStorageService;
    private final PythonExecutionService pythonExecutionService;
    private final JobRepository jobRepository;

    public QualityControlJob createJob(MultipartFile file, String profile) {
        // 1. Store File
        String filePath = fileStorageService.storeFile(file);

        // 2. Create DB Entity
        QualityControlJob job = new QualityControlJob();
        job.setOriginalFilename(file.getOriginalFilename());
        job.setFilePath(filePath);
        job.setProfile(profile);
        job.setStatus(QualityControlJob.JobStatus.PENDING);
        
        job = jobRepository.save(job);

        // 3. Trigger Async Analysis
        triggerAnalysis(job, profile);

        return job;
    }

    public void triggerAnalysis(QualityControlJob job, String profile) {
        job.setStatus(QualityControlJob.JobStatus.PROCESSING);
        jobRepository.save(job);

        pythonExecutionService.runAnalysis(job.getId(), job.getFilePath(), profile)
            .thenAccept(reportPath -> {
                job.setStatus(QualityControlJob.JobStatus.COMPLETED);
                job.setResultJsonPath(reportPath);
                job.setCompletedAt(LocalDateTime.now());
                jobRepository.save(job);
            })
            .exceptionally(ex -> {
                // Unwrap ExecutionException if present
                Throwable cause = ex.getCause() != null ? ex.getCause() : ex;

                if (cause instanceof com.spectra.aqc.service.PythonExecutionService.JobQueuedException) {
                    job.setStatus(QualityControlJob.JobStatus.QUEUED);
                    job.setErrorMessage(null); // Clear any previous error
                    // We don't set completedAt because it's not done
                } else {
                    job.setStatus(QualityControlJob.JobStatus.FAILED);
                    job.setErrorMessage(cause.getMessage());
                    job.setCompletedAt(LocalDateTime.now());
                }
                jobRepository.save(job);
                return null;
            });
    }

    public List<QualityControlJob> getAllJobs() {
        return jobRepository.findAllByOrderByCreatedAtDesc();
    }

    public Optional<QualityControlJob> getJob(Long id) {
        return jobRepository.findById(id);
    }

    public String getJobReport(Long id) {
        QualityControlJob job = jobRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("Job not found"));
        
        if (job.getResultJsonPath() == null) {
            throw new RuntimeException("Report not ready");
        }

        try {
            return java.nio.file.Files.readString(java.nio.file.Path.of(job.getResultJsonPath()));
        } catch (Exception e) {
            throw new RuntimeException("Failed to read report file", e);
        }
    }

    public String getJobVisual(Long id) {
        QualityControlJob job = jobRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("Job not found"));
        
        if (job.getResultJsonPath() == null) {
            throw new RuntimeException("Report not ready");
        }

        try {
            java.nio.file.Path jsonPath = java.nio.file.Path.of(job.getResultJsonPath());
            java.nio.file.Path visualPath = jsonPath.getParent().resolve("dashboard.html");
            return java.nio.file.Files.readString(visualPath);
        } catch (Exception e) {
            throw new RuntimeException("Failed to read visualization file", e);
        }
    }

    public java.io.File getJobVideoFile(Long id) {
        QualityControlJob job = jobRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("Job not found"));
        
        java.io.File file = new java.io.File(job.getFilePath());
        if (!file.exists()) {
            throw new RuntimeException("Video file not found at: " + job.getFilePath());
        }
        return file;
    }

    @org.springframework.transaction.annotation.Transactional
    public void deleteJob(Long id) {
        QualityControlJob job = jobRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("Job not found"));

        // 1. Delete associated files/directories
        if (job.getResultJsonPath() != null) {
            try {
                java.nio.file.Path reportDir = java.nio.file.Path.of(job.getResultJsonPath()).getParent();
                java.nio.file.Path jobUploadDir = reportDir.getParent();
                
                // Delete the entire job folder (e.g., uploads/job_1_...)
                if (java.nio.file.Files.exists(jobUploadDir)) {
                    org.springframework.util.FileSystemUtils.deleteRecursively(jobUploadDir);
                }
            } catch (Exception e) {
                System.err.println("Failed to delete job files: " + e.getMessage());
            }
        }

        // 2. Delete DB record
        jobRepository.delete(job);
    }

    @org.springframework.transaction.annotation.Transactional
    public void deleteJobs(java.util.List<Long> ids) {
        for (Long id : ids) {
            try {
                deleteJob(id);
            } catch (Exception e) {
                System.err.println("Failed to delete job " + id + ": " + e.getMessage());
            }
        }
    }

    public void triggerRemediation(Long jobId, String fixType) {
        QualityControlJob job = jobRepository.findById(jobId)
                .orElseThrow(() -> new RuntimeException("Job not found"));

        // Instead of running locally, we queue it
        // We hijack the 'profile' field to pass the fix type to the worker if needed, 
        // or we expect the worker to check 'fixType' (but our worker currently uses 'profile')
        // Let's use a convention: profile="REMEDIATION:<fixType>"
        
        job.setFixStatus("QUEUED");
        // We'll store the fix type in the profile temporarily for the worker to pick up, 
        // OR we just rely on the worker reading additional fields.
        // Since our worker reads 'profile', let's use that for simplicity in the immediate term.
        // A cleaner way would be to have a separate 'taskType' field, but we are patching.
        job.setProfile("REMEDIATION:" + fixType);
        
        jobRepository.save(job);
        
        // Remove local execution
        /*
        pythonExecutionService.runRemediation(job.getId(), job.getFilePath(), fixType)
            .thenAccept(fixedPath -> {
                job.setFixStatus("COMPLETED");
                job.setFixedFilePath(fixedPath);
                jobRepository.save(job);
            })
            .exceptionally(ex -> {
                job.setFixStatus("FAILED");
                job.setErrorMessage("Remediation Failed: " + ex.getMessage());
                jobRepository.save(job);
                return null;
            });
        */
    }

    // --- Remote Worker Methods ---

    public List<QualityControlJob> getQueuedJobs() {
        List<QualityControlJob> analysisJobs = jobRepository.findByStatus(QualityControlJob.JobStatus.QUEUED);
        List<QualityControlJob> remediationJobs = jobRepository.findByFixStatus("QUEUED");
        
        // Combine lists
        java.util.List<QualityControlJob> allJobs = new java.util.ArrayList<>(analysisJobs);
        allJobs.addAll(remediationJobs);
        return allJobs;
    }

    public synchronized QualityControlJob claimJob(Long id) {
        QualityControlJob job = jobRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("Job not found"));
        
        if (job.getStatus() == QualityControlJob.JobStatus.QUEUED) {
             job.setStatus(QualityControlJob.JobStatus.PROCESSING);
             return jobRepository.save(job);
        } else if ("QUEUED".equals(job.getFixStatus())) {
             job.setFixStatus("PROCESSING");
             return jobRepository.save(job);
        } else {
             throw new RuntimeException("Job " + id + " is not in QUEUED state.");
        }
    }

    public void completeJobRemote(Long id, String reportJsonContent, String reportHtmlContent, String errorMessage) {
        QualityControlJob job = jobRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("Job not found"));
        
        if (errorMessage != null && !errorMessage.isEmpty()) {
            job.setStatus(QualityControlJob.JobStatus.FAILED);
            job.setErrorMessage(errorMessage);
            job.setCompletedAt(LocalDateTime.now());
        } else {
            // Write JSON to file
            try {
                // Ensure directory exists
                java.nio.file.Path existingPath = java.nio.file.Path.of(job.getFilePath());
                String timestamp = LocalDateTime.now().format(java.time.format.DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss"));
                java.nio.file.Path uploadDir = existingPath.getParent();
                java.nio.file.Path resultDir = uploadDir.resolve("job_" + id + "_remote_" + timestamp);
                java.nio.file.Files.createDirectories(resultDir);
                
                java.nio.file.Path reportPath = resultDir.resolve("Master_Report.json");
                java.nio.file.Files.writeString(reportPath, reportJsonContent);

                // Save HTML Dashboard if provided
                if (reportHtmlContent != null && !reportHtmlContent.isEmpty()) {
                    java.nio.file.Path visualPath = resultDir.resolve("dashboard.html");
                    java.nio.file.Files.writeString(visualPath, reportHtmlContent);
                }
                
                job.setResultJsonPath(reportPath.toAbsolutePath().toString());
                job.setStatus(QualityControlJob.JobStatus.COMPLETED);
                job.setCompletedAt(LocalDateTime.now());
                
            } catch (Exception e) {
                job.setStatus(QualityControlJob.JobStatus.FAILED);
                job.setErrorMessage("Failed to save remote report: " + e.getMessage());
                job.setCompletedAt(LocalDateTime.now());
            }
        }
        jobRepository.save(job);
    }
    
    public void completeRemediationRemote(Long id, MultipartFile file) {
        QualityControlJob job = jobRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("Job not found"));
        
        try {
            // Save the uploaded file
            java.nio.file.Path originalPath = java.nio.file.Path.of(job.getFilePath());
            String originalName = originalPath.getFileName().toString();
            String nameWithoutExt = originalName.lastIndexOf('.') > 0 ? originalName.substring(0, originalName.lastIndexOf('.')) : originalName;
            String ext = originalName.lastIndexOf('.') > 0 ? originalName.substring(originalName.lastIndexOf('.')) : ".mp4";
            
            String fixedFilename = nameWithoutExt + "_fixed_remote" + ext;
            java.nio.file.Path fixedPath = originalPath.getParent().resolve(fixedFilename);
            
            file.transferTo(fixedPath.toFile());
            
            job.setFixedFilePath(fixedPath.toAbsolutePath().toString());
            job.setFixStatus("COMPLETED");
            
        } catch (Exception e) {
             job.setFixStatus("FAILED");
             job.setErrorMessage("Failed to save remote remediated file: " + e.getMessage());
        }
        jobRepository.save(job);
    }
}
