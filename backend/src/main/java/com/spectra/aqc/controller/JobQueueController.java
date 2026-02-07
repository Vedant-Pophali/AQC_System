package com.spectra.aqc.controller;

import com.spectra.aqc.model.QualityControlJob;
import com.spectra.aqc.service.QualityControlService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/queue")
@RequiredArgsConstructor
@CrossOrigin(origins = "*") // Allow Remote Worker Connectivity if needed
public class JobQueueController {

    private final QualityControlService qcService;

    @GetMapping("/pending")
    public ResponseEntity<List<QualityControlJob>> getPendingJobs() {
        return ResponseEntity.ok(qcService.getQueuedJobs());
    }

    @PostMapping("/{id}/claim")
    public ResponseEntity<QualityControlJob> claimJob(@PathVariable Long id) {
        try {
            return ResponseEntity.ok(qcService.claimJob(id));
        } catch (RuntimeException e) {
            return ResponseEntity.badRequest().build();
        }
    }

    @PostMapping("/{id}/complete")
    public ResponseEntity<Void> completeJob(@PathVariable Long id, @RequestBody Map<String, String> payload) {
        String reportJson = payload.get("reportJson");
        String errorMessage = payload.get("error");
        
        qcService.completeJobRemote(id, reportJson, errorMessage);
        return ResponseEntity.ok().build();
    }
}
