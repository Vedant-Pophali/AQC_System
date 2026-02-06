package com.spectra.aqc.service;

import com.spectra.aqc.model.QualityControlJob;
import com.spectra.aqc.repository.JobRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.MockitoAnnotations;

import java.util.Optional;
import java.util.concurrent.CompletableFuture;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.*;

public class QualityControlServiceTest {

    @Mock
    private JobRepository jobRepository;

    @Mock
    private PythonExecutionService pythonExecutionService;

    @Mock
    private FileStorageService fileStorageService;

    @InjectMocks
    private QualityControlService qualityControlService;

    @BeforeEach
    public void setup() {
        MockitoAnnotations.openMocks(this);
    }

    @Test
    public void testTriggerRemediation_Success() {
        // Arrange
        Long jobId = 1L;
        QualityControlJob job = new QualityControlJob();
        job.setId(jobId);
        job.setFilePath("test_input.mp4");
        job.setFixStatus("PENDING");

        when(jobRepository.findById(jobId)).thenReturn(Optional.of(job));
        when(pythonExecutionService.runRemediation(anyLong(), anyString(), anyString()))
                .thenReturn(CompletableFuture.completedFuture("fixed_output.mp4"));

        // Act
        qualityControlService.triggerRemediation(jobId, "loudness_norm");

        // Assert
        verify(jobRepository, times(2)).save(job); // Once for PROCESSING, once for COMPLETED
        assert "COMPLETED".equals(job.getFixStatus());
        assert "fixed_output.mp4".equals(job.getFixedFilePath());
    }

    @Test
    public void testTriggerRemediation_JobNotFound() {
        when(jobRepository.findById(anyLong())).thenReturn(Optional.empty());

        try {
            qualityControlService.triggerRemediation(999L, "fix");
        } catch (RuntimeException e) {
            assert "Job not found".equals(e.getMessage());
        }
    }
}
