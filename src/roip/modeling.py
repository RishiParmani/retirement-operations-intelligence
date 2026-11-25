import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder,StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report,roc_auc_score
from sklearn.model_selection import train_test_split

FEATURES=["operation_type","priority","channel","region","processing_team","team_workload","customer_segment","exception_flag","exception_type","rework_flag","sla_target_hours","received_month","received_day_of_week"]

def train_sla_model(df):
    completed=df[df.status=="Completed"].copy()
    X=completed[FEATURES]
    y=completed.sla_breached.astype(int)
    cat=[c for c in FEATURES if X[c].dtype=="object"]
    num=[c for c in FEATURES if c not in cat]
    prep=ColumnTransformer([("cat",Pipeline([("impute",SimpleImputer(strategy="most_frequent")),("ohe",OneHotEncoder(handle_unknown="ignore"))]),cat),
                          ("num",Pipeline([("impute",SimpleImputer(strategy="median")),("scale",StandardScaler())]),num)])
    Xtr,Xte,ytr,yte=train_test_split(X,y,test_size=.2,random_state=42,stratify=y)
    model=Pipeline([("preprocess",prep),("classifier",RandomForestClassifier(n_estimators=150,max_depth=12,min_samples_leaf=4,class_weight="balanced",random_state=42,n_jobs=-1))])
    model.fit(Xtr,ytr)
    pred=model.predict(Xte); proba=model.predict_proba(Xte)[:,1]
    return model,{"classification_report":classification_report(yte,pred,output_dict=True),"roc_auc":float(roc_auc_score(yte,proba)),"test_rows":len(yte)}
