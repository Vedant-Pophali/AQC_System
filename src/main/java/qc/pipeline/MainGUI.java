package qc.pipeline;

import javax.swing.*;
import javax.swing.border.EmptyBorder;
import java.awt.*;
import java.io.File;

public class MainGUI extends JFrame {

    private final JTextField filePathField;
    private final JTextArea logArea;
    private final JButton runButton;
    private final JButton openReportButton;
    private final WorkflowManager workflowManager;

    public MainGUI() {
        workflowManager = new WorkflowManager();

        // 1. WINDOW SETUP
        setTitle("AQC Professional Node (Enterprise Edition)");
        setSize(850, 550);
        setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
        setLocationRelativeTo(null);
        setLayout(new BorderLayout(10, 10));

        // 2. HEADER
        JPanel headerPanel = new JPanel(new FlowLayout(FlowLayout.LEFT));
        headerPanel.setBackground(new Color(33, 37, 43));
        JLabel titleLabel = new JLabel(" AQC SYSTEM | DISTRIBUTED ENGINE");
        titleLabel.setForeground(Color.WHITE);
        titleLabel.setFont(new Font("SansSerif", Font.BOLD, 18));
        titleLabel.setBorder(new EmptyBorder(15, 15, 15, 15));
        headerPanel.add(titleLabel);
        add(headerPanel, BorderLayout.NORTH);

        // 3. CONTROL PANEL
        JPanel controlPanel = new JPanel(new GridBagLayout());
        controlPanel.setBorder(new EmptyBorder(20, 20, 10, 20));
        GridBagConstraints gbc = new GridBagConstraints();
        gbc.insets = new Insets(5, 5, 5, 5);

        // Label
        gbc.gridx = 0; gbc.gridy = 0; gbc.gridwidth = 2; gbc.anchor = GridBagConstraints.WEST;
        controlPanel.add(new JLabel("Select Media Asset:"), gbc);

        // File Path Input
        filePathField = new JTextField();
        filePathField.setEditable(false);
        filePathField.setPreferredSize(new Dimension(500, 35));
        gbc.gridx = 0; gbc.gridy = 1; gbc.gridwidth = 1; gbc.fill = GridBagConstraints.HORIZONTAL;
        gbc.weightx = 1.0;
        controlPanel.add(filePathField, gbc);

        // Browse Button
        JButton browseButton = new JButton("Browse...");
        styleButton(browseButton, new Color(220, 220, 220), Color.BLACK);
        gbc.gridx = 1; gbc.gridy = 1; gbc.weightx = 0;
        controlPanel.add(browseButton, gbc);

        // Run Button (FIXED: Black Text)
        runButton = new JButton("START PIPELINE");
        // Green Background, BLACK Text (Always Visible)
        styleButton(runButton, new Color(46, 139, 87), Color.BLACK);
        runButton.setFont(new Font("SansSerif", Font.BOLD, 16));
        runButton.setEnabled(false);
        gbc.gridx = 0; gbc.gridy = 2; gbc.gridwidth = 2; gbc.fill = GridBagConstraints.HORIZONTAL;
        gbc.insets = new Insets(15, 5, 5, 5);
        controlPanel.add(runButton, gbc);

        add(controlPanel, BorderLayout.CENTER);

        // 4. LOG AREA
        JPanel bottomPanel = new JPanel(new BorderLayout());
        logArea = new JTextArea();
        logArea.setEditable(false);
        logArea.setFont(new Font("Monospaced", Font.PLAIN, 12));
        logArea.setBackground(new Color(240, 240, 245));
        logArea.setMargin(new Insets(10, 10, 10, 10));

        JScrollPane scrollPane = new JScrollPane(logArea);
        scrollPane.setPreferredSize(new Dimension(800, 250));
        scrollPane.setBorder(BorderFactory.createTitledBorder("Execution Logs"));

        bottomPanel.add(scrollPane, BorderLayout.CENTER);

        // Report Button (FIXED: Black Text)
        openReportButton = new JButton("Open Dashboard Report");
        // Blue Background, BLACK Text
        styleButton(openReportButton, new Color(100, 149, 237), Color.BLACK);
        openReportButton.setEnabled(false);
        bottomPanel.add(openReportButton, BorderLayout.SOUTH);

        add(bottomPanel, BorderLayout.SOUTH);

        // --- LISTENERS ---
        browseButton.addActionListener(e -> {
            JFileChooser fileChooser = new JFileChooser();
            fileChooser.setCurrentDirectory(new File(System.getProperty("user.dir")));
            int result = fileChooser.showOpenDialog(this);
            if (result == JFileChooser.APPROVE_OPTION) {
                File selectedFile = fileChooser.getSelectedFile();
                filePathField.setText(selectedFile.getAbsolutePath());
                runButton.setEnabled(true);
                log("Asset Selected: " + selectedFile.getName());
            }
        });

        runButton.addActionListener(e -> startAnalysis());

        openReportButton.addActionListener(e -> {
            String reportPath = "reports/dashboard.html";
            try {
                File htmlFile = new File(reportPath);
                if (htmlFile.exists()) Desktop.getDesktop().browse(htmlFile.toURI());
            } catch (Exception ex) {
                log("Error opening report: " + ex.getMessage());
            }
        });
    }

    private void startAnalysis() {
        String videoPath = filePathField.getText();
        runButton.setEnabled(false);
        openReportButton.setEnabled(false);
        logArea.setText("");

        // Pass 'this::log' so WorkflowManager can print here
        SwingWorker<Boolean, String> worker = new SwingWorker<>() {
            @Override
            protected Boolean doInBackground() {
                try {
                    workflowManager.runQualityControlPipeline(videoPath, MainGUI.this::log);
                    return true;
                } catch (Exception e) {
                    log("CRITICAL ERROR: " + e.getMessage());
                    e.printStackTrace();
                    return false;
                }
            }

            @Override
            protected void done() {
                runButton.setEnabled(true);
                openReportButton.setEnabled(true);
                JOptionPane.showMessageDialog(MainGUI.this, "Analysis Complete!", "Success", JOptionPane.INFORMATION_MESSAGE);
            }
        };
        worker.execute();
    }

    private void styleButton(JButton btn, Color bg, Color fg) {
        btn.setBackground(bg);
        btn.setForeground(fg); // This sets the text color
        btn.setFocusPainted(false);
        btn.setFont(new Font("SansSerif", Font.BOLD, 14));
        btn.setBorder(BorderFactory.createEmptyBorder(10, 20, 10, 20));
    }

    public void log(String message) {
        SwingUtilities.invokeLater(() -> {
            logArea.append(message + "\n");
            logArea.setCaretPosition(logArea.getDocument().getLength());
        });
    }

    public static void main(String[] args) {
        try { UIManager.setLookAndFeel(UIManager.getSystemLookAndFeelClassName()); } catch (Exception ignored) {}
        SwingUtilities.invokeLater(() -> new MainGUI().setVisible(true));
    }
}