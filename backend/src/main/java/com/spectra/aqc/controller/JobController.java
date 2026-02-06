package com.spectra.aqc.controller;

import com.spectra.aqc.model.QualityControlJob;
import com.spectra.aqc.service.QualityControlService;
import lombok.RequiredArgsConstructor;
import org.springframework.core.io.FileSystemResource;
import org.springframework.core.io.Resource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.io.File;
import java.util.List;

@RestController
@RequestMapping("/api/v1/jobs")
@RequiredArgsConstructor
@CrossOrigin(origins = "*") // Allow React Frontend
public class JobController {

    private final QualityControlService qcService;

    @PostMapping
    public ResponseEntity<QualityControlJob> uploadFile(
            @RequestParam("file") MultipartFile file,
            @RequestParam(value = "profile", defaultValue = "strict") String profile) {
        QualityControlJob job = qcService.createJob(file, profile);
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

    @GetMapping("/{id}/visual")
    public ResponseEntity<String> getJobVisual(@PathVariable Long id) {
        try {
            String html = qcService.getJobVisual(id);
            return ResponseEntity.ok()
                    .contentType(org.springframework.http.MediaType.TEXT_HTML)
                    .body(html);
        } catch (RuntimeException e) {
            return ResponseEntity.badRequest().body("<html><body><h1>Error</h1><p>" + e.getMessage() + "</p></body></html>");
        }
    }

    @GetMapping("/{id}/video")
    public ResponseEntity<Resource> getJobVideo(@PathVariable Long id) {
        try {
            File videoFile = qcService.getJobVideoFile(id);
            Resource resource = new FileSystemResource(videoFile);
            
            return ResponseEntity.ok()
                    .contentType(MediaType.parseMediaType("video/mp4"))
                    .header(HttpHeaders.CONTENT_DISPOSITION, "inline; filename=\"" + videoFile.getName() + "\"")
                    .body(resource);
        } catch (Exception e) {
            return ResponseEntity.notFound().build();
        }
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteJob(@PathVariable Long id) {
        try {
            qcService.deleteJob(id);
            return ResponseEntity.noContent().build();
        } catch (RuntimeException e) {
            return ResponseEntity.notFound().build();
        }
    }

    @DeleteMapping("/batch")
    public ResponseEntity<Void> deleteJobs(@RequestBody java.util.List<Long> ids) {
        qcService.deleteJobs(ids);
        return ResponseEntity.noContent().build();
    }

    @PostMapping("/{id}/fix")
    public ResponseEntity<Void> triggerRemediation(@PathVariable Long id, @RequestBody java.util.Map<String, String> payload) {
        String fixType = payload.get("fixType");
        if (fixType == null) {
            return ResponseEntity.badRequest().build();
        }
        qcService.triggerRemediation(id, fixType);
        return ResponseEntity.accepted().build();
    }

    @GetMapping("/{id}/fixed-download")
    public ResponseEntity<Resource> downloadFixedVideo(@PathVariable Long id) {
        try {
            com.spectra.aqc.model.QualityControlJob job = qcService.getJob(id)
                .orElseThrow(() -> new RuntimeException("Job not found"));
            
            if (job.getFixedFilePath() == null) {
                return ResponseEntity.notFound().build();
            }

            File videoFile = new File(job.getFixedFilePath());
            if (!videoFile.exists()) {
                 return ResponseEntity.notFound().build();
            }
            
            Resource resource = new FileSystemResource(videoFile);
            
            return ResponseEntity.ok()
                    .contentType(MediaType.parseMediaType("video/mp4"))
                    .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"" + videoFile.getName() + "\"")
                    .body(resource);
        } catch (Exception e) {
            return ResponseEntity.notFound().build();
        }
    }
}
