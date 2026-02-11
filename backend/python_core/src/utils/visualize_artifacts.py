import matplotlib.pyplot as plt
import matplotlib.patches as patches
import os
import logging
from typing import List, Dict, Optional

# Configure logger
logger = logging.getLogger(__name__)

def plot_artifact_timeline(
    results: List[Dict], 
    output_path: str, 
    thresholds: Optional[Dict[str, float]] = None
) -> None:
    """
    Generate a timeline chart of BRISQUE artifact scores.
    
    Args:
        results: List of dicts from artifact_scorer.analyze_video()
                 Each dict must have 'timestamp' and 'score'.
        output_path: Path to save the PNG image.
        thresholds: Dict defining color zones (mild/moderate/severe).
                    Defaults to standard calibration if None.
    """
    if not results:
        logger.warning("No results to visualize.")
        return

    # Extract data
    timestamps = [r['timestamp'] for r in results]
    scores = [r['score'] for r in results]
    
    # Default thresholds for visualization zones
    if thresholds is None:
        thresholds = {"mild": 40.0, "moderate": 55.0, "severe": 75.0}

    # Setup Plot
    plt.figure(figsize=(12, 6))
    ax = plt.gca()
    
    # Plot the Data Line
    plt.plot(timestamps, scores, color='#2c3e50', linewidth=2, label='BRISQUE Score')
    plt.scatter(timestamps, scores, color='#2c3e50', s=10)

    # -------------------------------------------------------
    # Color Zones (Background)
    # -------------------------------------------------------
    # We want to fill the background to indicate quality levels.
    # Y-axis range for plot
    y_max = max(100, max(scores) + 10)
    
    # Green Zone (Clean: 0 to Mild)
    rect_clean = patches.Rectangle((0, 0), max(timestamps), thresholds['mild'], 
                                 linewidth=0, facecolor='#2ecc71', alpha=0.15, label='Clean')
    ax.add_patch(rect_clean)

    # Yellow Zone (Mild/Moderate: Mild to Moderate)
    rect_mild = patches.Rectangle((0, thresholds['mild']), max(timestamps), 
                                thresholds['moderate'] - thresholds['mild'], 
                                linewidth=0, facecolor='#f1c40f', alpha=0.15, label='Mild Artifacts')
    ax.add_patch(rect_mild)

    # Orange Zone (Moderate: Moderate to Severe)
    rect_mod = patches.Rectangle((0, thresholds['moderate']), max(timestamps), 
                               thresholds['severe'] - thresholds['moderate'], 
                               linewidth=0, facecolor='#e67e22', alpha=0.15, label='Visible Artifacts')
    ax.add_patch(rect_mod)

    # Red Zone (Severe: > Severe)
    rect_sev = patches.Rectangle((0, thresholds['severe']), max(timestamps), 
                               y_max - thresholds['severe'], 
                               linewidth=0, facecolor='#e74c3c', alpha=0.15, label='Severe Artifacts')
    ax.add_patch(rect_sev)

    # -------------------------------------------------------
    # Formatting
    # -------------------------------------------------------
    plt.title("Compression Artifact Analysis (BRISQUE)", fontsize=14, pad=15)
    plt.xlabel("Time (seconds)", fontsize=12)
    plt.ylabel("Artifact Score (Lower is Better)", fontsize=12)
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.xlim(0, max(timestamps))
    plt.ylim(0, y_max)
    
    # Add passing threshold line (Visual guide)
    plt.axhline(y=thresholds['moderate'], color='red', linestyle='--', alpha=0.5, label='Rejection Threshold')
    
    plt.legend(loc='upper right')
    
    # Save
    try:
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        logger.info(f"Artifact timeline saved to: {output_path}")
        plt.close() # Free memory
    except Exception as e:
        logger.error(f"Failed to save visualization: {e}")

# Self-test
if __name__ == "__main__":
    # Create dummy data
    import numpy as np
    
    dummy_results = []
    for t in range(0, 60, 2):
        # Simulate a degradation event in the middle
        base_score = 30
        if 20 < t < 40:
            base_score = 75 # Spike
        
        score = base_score + np.random.randint(-5, 5)
        dummy_results.append({"timestamp": float(t), "score": float(score)})
        
    logging.basicConfig(level=logging.INFO)
    plot_artifact_timeline(dummy_results, "test_artifact_plot.png")
    print("✅ Test plot generated: test_artifact_plot.png")