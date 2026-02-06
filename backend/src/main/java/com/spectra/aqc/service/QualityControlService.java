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
                job.setStatus(QualityControlJob.JobStatus.FAILED);
                job.setErrorMessage(ex.getMessage());
                job.setCompletedAt(LocalDateTime.now());
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

        job.setFixStatus("PROCESSING");
        jobRepository.save(job);

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
    }
}
