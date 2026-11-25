import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd, json
from src.roip.modeling import train_sla_model

if __name__=='__main__':
    df=pd.read_csv('data/processed/operations_clean.csv')
    model,metrics=train_sla_model(df)
    Path('reports').mkdir(exist_ok=True)
    with open('reports/model_metrics.json','w') as f: json.dump(metrics,f,indent=2)
    print('ROC-AUC:',metrics['roc_auc'])
    print(json.dumps(metrics['classification_report'],indent=2))
