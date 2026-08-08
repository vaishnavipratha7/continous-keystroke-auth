import os
import pandas as pd
import numpy as np
import time
from pathlib import Path

# Use relative paths based on script location
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
FREE_TEXT_CSV = PROJECT_ROOT / "data" / "free-text.csv"
OUTPUT_CSV = PROJECT_ROOT / "data" / "reconstructed_events.csv"

def parse_keystrokes():
    print("Loading free-text.csv...")
    start_time = time.time()
    df = pd.read_csv(FREE_TEXT_CSV, low_memory=False)
    print(f"Loaded {len(df)} raw digraph rows in {time.time() - start_time:.2f} seconds.")
    
    # Strip column names just in case there are spaces
    df.columns = [c.strip() for c in df.columns]
    
    # Clean the numeric columns: convert to float, coercing errors to NaN
    numeric_cols = ['DU.key1.key1', 'DD.key1.key2', 'DU.key1.key2', 'UD.key1.key2', 'UU.key1.key2']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
    # Drop rows that have NaN in critical fields
    initial_len = len(df)
    df = df.dropna(subset=['participant', 'session', 'key1', 'key2', 'DU.key1.key1', 'DD.key1.key2', 'DU.key1.key2'])
    dropped = initial_len - len(df)
    if dropped > 0:
        print(f"Dropped {dropped} malformed/non-numeric rows.")
        
    print("Grouping and reconstructing events...")
    reconstructed_rows = []
    
    # Group by participant and session
    grouped = df.groupby(['participant', 'session'])
    
    total_sessions = len(grouped)
    session_count = 0
    chain_break_count = 0
    chain_continue_count = 0
    
    for (participant, session), group in grouped:
        session_count += 1
        if session_count % 20 == 0 or session_count == total_sessions:
            print(f"Processing session {session_count}/{total_sessions}...")
            
        # Convert group to list of dicts for speed
        records = group.to_dict('records')
        if not records:
            continue
            
        events = []
        
        # Row 0
        row0 = records[0]
        k1 = str(row0['key1'])
        k2 = str(row0['key2'])
        dwell_k1 = float(row0['DU.key1.key1'])
        dd = float(row0['DD.key1.key2'])
        du = float(row0['DU.key1.key2'])
        
        down_k1 = 0.0
        up_k1 = dwell_k1
        
        down_k2 = down_k1 + dd
        up_k2 = down_k1 + du
        
        events.append({'key': k1, 'down_time': down_k1, 'up_time': up_k1})
        events.append({'key': k2, 'down_time': down_k2, 'up_time': up_k2})
        
        prev_down_k2 = down_k2
        prev_key2 = k2
        
        for idx in range(1, len(records)):
            row = records[idx]
            k1 = str(row['key1'])
            k2 = str(row['key2'])
            dwell_k1 = float(row['DU.key1.key1'])
            dd = float(row['DD.key1.key2'])
            du = float(row['DU.key1.key2'])
            
            # Chain link
            if k1 == prev_key2:
                down_k1 = prev_down_k2
                chain_continue_count += 1
            else:
                # Chain broken, start a new chain relative to previous events' max up_time
                last_up = max(e['up_time'] for e in events)
                down_k1 = last_up + 1.0
                chain_break_count += 1
                up_k1 = down_k1 + dwell_k1
                events.append({'key': k1, 'down_time': down_k1, 'up_time': up_k1})
                
            down_k2 = down_k1 + dd
            up_k2 = down_k1 + du
            events.append({'key': k2, 'down_time': down_k2, 'up_time': up_k2})
            
            prev_down_k2 = down_k2
            prev_key2 = k2
            
        # Shift times so that min(down_time) in this session is 0.0
        min_down = min(e['down_time'] for e in events)
        for e in events:
            # Add participant and session details
            reconstructed_rows.append({
                'participant': participant,
                'session': session,
                'key': e['key'],
                'down_time': e['down_time'] - min_down,
                'up_time': e['up_time'] - min_down
            })
            
    print(f"Reconstructed {len(reconstructed_rows)} individual key events.")
    
    # Report chain statistics
    total_chains = chain_break_count + chain_continue_count
    if total_chains > 0:
        chain_break_pct = (chain_break_count / total_chains) * 100
        print(f"\n=== Chain Statistics ===")
        print(f"Chain continuations: {chain_continue_count}")
        print(f"Chain breaks (fabricated 1.0s gap): {chain_break_count}")
        print(f"Chain break percentage: {chain_break_pct:.2f}%")
    
    print("Creating dataframe and sorting...")
    out_df = pd.DataFrame(reconstructed_rows)
    # Sort within each participant and session by down_time
    out_df = out_df.sort_values(by=['participant', 'session', 'down_time']).reset_index(drop=True)
    
    print(f"Saving to {OUTPUT_CSV}...")
    out_df.to_csv(OUTPUT_CSV, index=False)
    print("Done!")

if __name__ == "__main__":
    parse_keystrokes()
