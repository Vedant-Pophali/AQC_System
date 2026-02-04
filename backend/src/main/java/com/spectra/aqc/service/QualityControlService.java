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

    public QualityControlJob createJob(MultipartFile file) {
        // 1. Store File
        String filePath = fileStorageService.storeFile(file);

        // 2. Create DB Entitiy
        QualityControlJob job = new QualityControlJob();
        job.setOriginalFilename(file.getOriginalFilename());
        job.setFilePath(filePath);
        job = jobRepository.save(job);

        // 3. Trigger Async Analysis
        triggerAnalysis(job);

        return job;
    }

    private void triggerAnalysis(QualityControlJob job) {
        job.setStatus(QualityControlJob.JobStatus.PROCESSING);
        jobRepository.save(job);

        pythonExecutionService.runAnalysis(job.getId(), job.getFilePath())
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
        return jobRepository.findAll();
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
}
