import pandas as pd

def ajouter_totaux(df, colonnes_totaux):
    if df.empty:
        return {col: 0 for col in colonnes_totaux}

    totaux = {}
    for col in colonnes_totaux:
        if col in df.columns:
            totaux[col] = pd.to_numeric(df[col], errors="coerce").sum()
        else:
            totaux[col] = 0
    return totaux

def color_rows(row):
    if row.get('Synchro_MMS') == 'Oui':
        return ['background-color: lightgreen'] * len(row)
    else:
        return ['background-color: lightcoral'] * len(row)

def update_emplacement(row):
    prefix = row.get('prefix_emplacement', '')
    emp = row.get('Emplacement', '')
    if prefix == 'IN':
        return f"{prefix}-{emp}"
    elif prefix == 'UNLOADING':
        return 'DECHARGEMENT'
    elif prefix == 'INSPECTION':
        return f"LITIGES-{emp}"
    else:
        return emp
