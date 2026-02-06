package com.spectra.aqc.controller;

import com.spectra.aqc.service.QualityControlService;
import com.spectra.aqc.model.QualityControlJob;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.MockitoAnnotations;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;

import java.util.Optional;
import java.util.Map;
import java.util.HashMap;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.*;

public class JobControllerTest {

    @Mock
    private QualityControlService qcService;

    @InjectMocks
    private JobController jobController;

    @BeforeEach
    public void setup() {
        MockitoAnnotations.openMocks(this);
    }

    @Test
    public void testTriggerRemediation_Accepted() {
        Long jobId = 1L;
        Map<String, String> payload = new HashMap<>();
        payload.put("fixType", "combined_fix");

        doNothing().when(qcService).triggerRemediation(anyLong(), anyString());

        ResponseEntity<Void> response = jobController.triggerRemediation(jobId, payload);

        assert response.getStatusCode() == HttpStatus.ACCEPTED;
        verify(qcService).triggerRemediation(1L, "combined_fix");
    }

    @Test
    public void testTriggerRemediation_BadRequest() {
        Long jobId = 1L;
        Map<String, String> payload = new HashMap<>();
        // Missing fixType

        ResponseEntity<Void> response = jobController.triggerRemediation(jobId, payload);

        assert response.getStatusCode() == HttpStatus.BAD_REQUEST;
        verify(qcService, never()).triggerRemediation(anyLong(), anyString());
    }

    @Test
    public void testDownloadFixedVideo_NotFound_NoFile() {
        Long jobId = 1L;
        QualityControlJob job = new QualityControlJob();
        job.setId(jobId);
        job.setFixedFilePath(null); // No file path

        when(qcService.getJob(jobId)).thenReturn(Optional.of(job));

        ResponseEntity<?> response = jobController.downloadFixedVideo(jobId);

        assert response.getStatusCode() == HttpStatus.NOT_FOUND;
    }
}
