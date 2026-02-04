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

    @Enumerated(EnumType.STRING)
    private JobStatus status;

    private LocalDateTime createdAt;
    private LocalDateTime completedAt;

    @Column(columnDefinition = "TEXT")
    private String resultJsonPath;

    @Column(columnDefinition = "TEXT")
    private String errorMessage;

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
}
