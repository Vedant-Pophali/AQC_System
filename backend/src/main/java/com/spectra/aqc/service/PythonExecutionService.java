package com.spectra.aqc.service;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import java.io.BufferedReader;
import java.io.File;
import java.io.InputStreamReader;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.concurrent.CompletableFuture;

@Service
public class PythonExecutionService {

    @Value("${app.aqc.script-path:../../main.py}")
    private String scriptPath;
    
    @Value("${app.storage.upload-dir}")
    private String outputDir;

    public CompletableFuture<String> runAnalysis(Long jobId, String inputFilePath) {
        return CompletableFuture.supplyAsync(() -> {
            try {
                File scriptFile = new File(scriptPath).getCanonicalFile();
                if (!scriptFile.exists()) {
                    throw new RuntimeException("Python script not found at: " + scriptFile.getAbsolutePath());
                }

                String timestamp = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss"));
                String resultDirName = "job_" + jobId + "_" + timestamp;
                Path resultDir = Paths.get(outputDir).resolve(resultDirName).toAbsolutePath();
                
                // Construct command: python main.py --input <file> --outdir <dir>
                ProcessBuilder pb = new ProcessBuilder(
                    "python",
                    scriptFile.getAbsolutePath(),
                    "--input", inputFilePath,
                    "--outdir", resultDir.toString()
                );
                
                pb.redirectErrorStream(true);
                Process process = pb.start();

                // Capture output logic could go here (logging)
                try (BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream()))) {
                    String line;
                    while ((line = reader.readLine()) != null) {
                        System.out.println("[Job " + jobId + " Python]: " + line);
                    }
                }

                int exitCode = process.waitFor();
                if (exitCode != 0) {
                    throw new RuntimeException("Python script exited with code " + exitCode);
                }

                // Find report file (it might be in a subdir named after the video)
                try (java.util.stream.Stream<Path> stream = java.nio.file.Files.walk(resultDir)) {
                    Path reportPath = stream
                        .filter(p -> p.getFileName().toString().equals("Master_Report.json"))
                        .findFirst()
                        .orElseThrow(() -> new RuntimeException("Master_Report.json not found in " + resultDir));
                    return reportPath.toAbsolutePath().toString();
                }

            } catch (Exception e) {
                throw new RuntimeException("Analysis failed: " + e.getMessage(), e);
            }
        });
    }
}
