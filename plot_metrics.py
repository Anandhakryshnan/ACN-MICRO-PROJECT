import pandas as pd
import matplotlib.pyplot as plt

def main():
    try:
        df = pd.read_csv('jitter_metrics.csv')
    except FileNotFoundError:
        print("jitter_metrics.csv not found. Please run sender.py and receiver.py to generate data.")
        return

    if df.empty:
        print("No data in jitter_metrics.csv.")
        return

    plt.figure(figsize=(10, 6))
    
    # Plot Transit Delay (n_i)
    plt.plot(df['seq_num'], df['transit_delay'], label='Transit Delay ($n_i$)', color='blue', alpha=0.6, linewidth=1.5)
    
    # Plot Playout Target Window (p_i)
    plt.plot(df['seq_num'], df['playout_target'], label='Playout Target Window ($p_i$)', color='red', alpha=0.8, linewidth=2)
    
    plt.title('VoIP Engine: Adaptive Jitter Management Analysis')
    plt.xlabel('Sequence Number')
    plt.ylabel('Delay (ms)')
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.tight_layout()
    
    plt.savefig('jitter_analysis.png', dpi=300)
    print("Plot saved to jitter_analysis.png")
    
if __name__ == "__main__":
    main()
