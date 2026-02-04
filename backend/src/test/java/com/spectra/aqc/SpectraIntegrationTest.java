package com.spectra.aqc;

import com.spectra.aqc.model.QualityControlJob;
import com.spectra.aqc.repository.JobRepository;
import com.spectra.aqc.service.PythonExecutionService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.MediaType;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.web.servlet.MockMvc;

import java.util.concurrent.CompletableFuture;

import static org.hamcrest.Matchers.*;
import static org.mockito.ArgumentMatchers.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
class SpectraIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private JobRepository jobRepository;

    @MockBean
    private PythonExecutionService pythonExecutionService;

    @BeforeEach
    void setup() {
        jobRepository.deleteAll();
    }

    @Test
    void testUploadAndJobCreation() throws Exception {
        // Mock Python Service to return immediate success
        Mockito.when(pythonExecutionService.runAnalysis(anyLong(), anyString()))
                .thenReturn(CompletableFuture.completedFuture("test-reports/report.json"));

        MockMultipartFile file = new MockMultipartFile(
                "file", 
                "test_vid.mp4", 
                MediaType.MULTIPART_FORM_DATA_VALUE, 
                "dummy content".getBytes()
        );

        mockMvc.perform(multipart("/api/v1/jobs").file(file))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.originalFilename", is("test_vid.mp4")))
                .andExpect(jsonPath("$.status", is("PENDING"))); // Logic sets it to PENDING initially

        // Verify it exists in DB
        assert jobRepository.count() == 1;
    }

    @Test
    void testGetJobStatus() throws Exception {
        QualityControlJob job = new QualityControlJob();
        job.setOriginalFilename("status_check.mp4");
        job.setFilePath("uploads/status_check.mp4");
        job = jobRepository.save(job);

        mockMvc.perform(get("/api/v1/jobs/" + job.getId()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id", is(job.getId().intValue())))
                .andExpect(jsonPath("$.originalFilename", is("status_check.mp4")));
    }
}
