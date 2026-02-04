package com.spectra.aqc.controller;

import com.spectra.aqc.model.QualityControlJob;
import com.spectra.aqc.service.QualityControlService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import java.util.List;

@RestController
@RequestMapping("/api/v1/jobs")
@RequiredArgsConstructor
@CrossOrigin(origins = "*") // Allow React Frontend
public class JobController {

    private final QualityControlService qcService;

    @PostMapping
    public ResponseEntity<QualityControlJob> uploadFile(@RequestParam("file") MultipartFile file) {
        QualityControlJob job = qcService.createJob(file);
        return ResponseEntity.ok(job);
    }

    @GetMapping
    public ResponseEntity<List<QualityControlJob>> listJobs() {
        return ResponseEntity.ok(qcService.getAllJobs());
    }

    @GetMapping("/{id}")
    public ResponseEntity<QualityControlJob> getJob(@PathVariable Long id) {
        return qcService.getJob(id)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @GetMapping("/{id}/report")
    public ResponseEntity<String> getJobReport(@PathVariable Long id) {
        try {
            String reportJson = qcService.getJobReport(id);
            return ResponseEntity.ok()
                    .contentType(org.springframework.http.MediaType.APPLICATION_JSON)
                    .body(reportJson);
        } catch (RuntimeException e) {
            return ResponseEntity.badRequest().body("{\"error\": \"" + e.getMessage() + "\"}");
        }
    }
}
