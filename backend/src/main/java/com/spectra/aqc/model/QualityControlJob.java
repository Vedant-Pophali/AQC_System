package com.spectra.aqc.model;

import jakarta.persistence.*;
import lombok.Data;
import java.time.LocalDateTime;

@Entity
@Table(name = "qc_jobs")
@Data
public class QualityControlJob {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private String originalFilename;

    @Column(nullable = false)
    private String filePath;

    private String profile;

    @Enumerated(EnumType.STRING)
    private JobStatus status;

    private LocalDateTime createdAt;
    private LocalDateTime completedAt;

    private String resultJsonPath;

    @Column(columnDefinition = "TEXT")
    private String errorMessage;
    
    // Remediation Fields
    private String fixedFilePath;
    private String fixStatus; // PENDING, PROCESSING, COMPLETED, FAILED

    @PrePersist
    protected void onCreate() {
        createdAt = LocalDateTime.now();
        status = JobStatus.PENDING;
    }

    public enum JobStatus {
        PENDING,
        PROCESSING,
        COMPLETED,
        FAILED
    }

    // Manual Getters/Setters to bypass Lombok issues
    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    
    public String getOriginalFilename() { return originalFilename; }
    public void setOriginalFilename(String originalFilename) { this.originalFilename = originalFilename; }
    
    public String getFilePath() { return filePath; }
    public void setFilePath(String filePath) { this.filePath = filePath; }
    
    public String getProfile() { return profile; }
    public void setProfile(String profile) { this.profile = profile; }
    
    public JobStatus getStatus() { return status; }
    public void setStatus(JobStatus status) { this.status = status; }
    
    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }
    
    public LocalDateTime getCompletedAt() { return completedAt; }
    public void setCompletedAt(LocalDateTime completedAt) { this.completedAt = completedAt; }
    
    public String getResultJsonPath() { return resultJsonPath; }
    public void setResultJsonPath(String resultJsonPath) { this.resultJsonPath = resultJsonPath; }
    
    public String getErrorMessage() { return errorMessage; }
    public void setErrorMessage(String errorMessage) { this.errorMessage = errorMessage; }

    public String getFixedFilePath() { return fixedFilePath; }
    public void setFixedFilePath(String fixedFilePath) { this.fixedFilePath = fixedFilePath; }

    public String getFixStatus() { return fixStatus; }
    public void setFixStatus(String fixStatus) { this.fixStatus = fixStatus; }
}
