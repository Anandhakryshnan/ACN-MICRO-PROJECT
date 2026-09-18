"""
plot_jitter.py
Generates a graph showing jitter variance.
"""

import pandas as pd
import matplotlib.pyplot as plt

def main():
    """
    Reads jitter_metrics.csv and plots Jitter Variance (v_i).
    """
    try:
        df = pd.read_csv('jitter_metrics.csv')
    except FileNotFoundError:
        print("jitter_metrics.csv not found.")
        return
    except pd.errors.EmptyDataError:
        print("No data in jitter_metrics.csv yet.")
        return

    if df.empty:
        print("No data in jitter_metrics.csv.")
        return

    plt.figure(figsize=(10, 4))

    # Plot Jitter (v_i)
    # pylint: disable=line-too-long
    plt.plot(df['seq_num'], df['jitter'], label='Jitter Variance ($v_i$)', color='purple', alpha=0.8, linewidth=2)

    plt.title('VoIP Engine: Jitter Variance Analysis')
    plt.xlabel('Sequence Number')
    plt.ylabel('Jitter Delay (ms)')
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.tight_layout()

    plt.savefig('jitter_variance.png', dpi=300)
    print("Plot saved to jitter_variance.png")

if __name__ == "__main__":
    main()
