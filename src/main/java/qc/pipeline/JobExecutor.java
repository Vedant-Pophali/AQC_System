package qc.pipeline;

import org.apache.commons.exec.CommandLine;
import org.apache.commons.exec.DefaultExecutor;
import org.apache.commons.exec.PumpStreamHandler;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.ByteArrayOutputStream;
import java.io.IOException;

public class JobExecutor {
    private static final Logger logger = LoggerFactory.getLogger(JobExecutor.class);

    public static class ExecutionResult {
        public int exitCode;
        public String outputLogs;
        public String errorLogs;

        public ExecutionResult(int exitCode, String outputLogs, String errorLogs) {
            this.exitCode = exitCode;
            this.outputLogs = outputLogs;
            this.errorLogs = errorLogs;
        }
    }

    public ExecutionResult executeCommand(CommandLine cmdLine) {
        DefaultExecutor executor = new DefaultExecutor();
        ByteArrayOutputStream outputStream = new ByteArrayOutputStream();
        ByteArrayOutputStream errorStream = new ByteArrayOutputStream();

        // This captures the text output from the command so Java can read it
        PumpStreamHandler streamHandler = new PumpStreamHandler(outputStream, errorStream);
        executor.setStreamHandler(streamHandler);

        // Don't crash Java if the command fails (we handle it manually)
        executor.setExitValues(null);

        try {
            logger.info("Executing: " + cmdLine.toString());
            int exitValue = executor.execute(cmdLine);
            return new ExecutionResult(exitValue, outputStream.toString(), errorStream.toString());
        } catch (IOException e) {
            logger.error("Execution failed", e);
            return new ExecutionResult(-1, "", "Exception: " + e.getMessage());
        }
    }
}