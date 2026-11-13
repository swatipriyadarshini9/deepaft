# Thesis results summary

Auto-generated from experiment outputs. **Do not edit numbers manually.**

## Simulation chapter (scenarios A–D)

Replications per scenario: **50**

Harrell C-index (mean across replications):

```
scenario                      A      B      C      D
model                                               
cox                       0.361  0.321  0.337  0.353
deepAFT_BJ                0.758  0.745  0.733  0.697
deepAFT_BJ_covariate        NaN  0.746    NaN  0.697
deepAFT_BJ_group_scale      NaN    NaN    NaN  0.697
deepAFT_IPCW_or_fallback    NaN    NaN  0.733    NaN
deepsurv                  0.720  0.703  0.682  0.661
lognormal                 0.706  0.686  0.663  0.648
rsf                       0.287  0.297  0.316  0.331
```

Standard deviation:

```
scenario                      A      B      C      D
model                                               
cox                       0.059  0.029  0.020  0.035
deepAFT_BJ                0.103  0.064  0.065  0.054
deepAFT_BJ_covariate        NaN  0.064    NaN  0.053
deepAFT_BJ_group_scale      NaN    NaN    NaN  0.054
deepAFT_IPCW_or_fallback    NaN    NaN  0.065    NaN
deepsurv                  0.039  0.036  0.026  0.041
lognormal                 0.041  0.036  0.029  0.039
rsf                       0.037  0.024  0.020  0.033
```

## Real-data benchmark — TCGA genes only (671 cases) — primary thesis benchmark (5-fold CV)

Feature sets: genes, radiomics (if linked), genes+radiomics. Interpret only if a defensible BraTS↔TCGA crosswalk exists for your imaging year.

```
features            model  c_index_mean  c_index_std  amse_mean  amse_std
   genes              cox      0.385564     0.039120  43.702422  7.316973
   genes deepAFT_BJ_group      0.749801     0.021722   2.482601  0.669488
   genes         deepsurv      0.718118     0.043259 621.960359 28.373260
   genes        lognormal      0.754787     0.023025   2.353964  0.503852
   genes              rsf      0.330238     0.030469  39.992098  6.591734
```

## Proportional hazards test (gene panel)

- Minimum Schoenfeld p (worst covariate): 0.02988447665868388
- Worst covariate: IDH1
- Per gene:
  - IDH1: p=0.02988
  - MGMT: p=0.3312
  - TP53: p=0.9765
- **PH rejected (p<0.05)** → AFT/deepAFT justified as alternative to Cox.

## Model choice — deepAFT vs Cox (justification)

This block interprets **your recorded outputs**. Cite Norman et al. (2024) for the deepAFT formulation; use Grambsch–Therneau / Schoenfeld on **your** covariates before preferring AFT in other cohorts.

### When deepAFT (or AFT more generally) is **justified here**

- **Proportional hazards doubtful on the gene panel:** minimum Schoenfeld p = 0.02988 (IDH1). Cox hazard ratios are hard to interpret when effects are time-varying; AFT targets log-time directly.
- **Discrimination on TCGA (genes, 5-fold CV):** Cox C-index 0.386 vs deepAFT_BJ_group 0.750 with PH violated — Cox underperforms under this mis-specification.
- **Parametric benchmark:** log-normal AFT 0.755 vs deepAFT_BJ_group 0.750; deepAFT is the neural log-time extension when linear AFT mean is too rigid (see simulation).
- **Simulation (mean C-index across scenarios A–D):** Cox 0.343 vs deepAFT_BJ 0.733 under Norman-style nonlinear log-time DGP — supports neural AFT when the true log-time surface is non-linear.
- **Known limitation settings (scenarios B–D):** use deepAFT covariate-censoring, IPCW fallback, or group-scale BJ when those assumptions are plausibly violated (see simulation chapter).

### When **not** to rely on deepAFT (or when Cox / simpler models suffice)

- **PH not rejected** (all Schoenfeld p > 0.05 on your covariates): prefer Cox for standard hazard interpretation; deepAFT is optional for *time prediction*, not required.
- **Hazard ratios only:** if the research question is relative hazard, not calibrated survival time, Cox (or penalized Cox) is the conventional choice.
- **Tiny samples / unstable censoring weights:** IPCW paths can fail; this package falls back to Buckley–James — still prefer simpler AFT or Cox when n is small.
- **BraTS imaging chapters:** PTG glioma-type and site prediction use classification metrics, not Cox/deepAFT — survival models apply to TCGA OS, not unlabeled PTG MRI alone.
- **No linked multimodal OS on 2024 PTG:** until crosswalk IDs overlap features (see linkage report), do not claim deepAFT on imaging+genes for the full BraTS cohort.
- **Domain shift:** project holdout (LGG→GBM / GBM→LGG) shows modest C-index (~0.49–0.52 for log-normal AFT in `glioma_benchmark_external.csv`) — high in-sample CV does not imply deepAFT replaces clinical stratification on external projects.

## BraTS 2024 GLI cohort (local data)

```
            split_folder  n_cases
       training_data1_v2     1350
training_data_additional      271
         validation_data      188
                  _TOTAL     1809
               _WITH_SEG     1621
```

## BraTS 2024 validation split (modality QC)

```
 n_cases  all_four_modalities  with_seg
     188                  188         0
```

## BraTS imaging — Imaging features vs PTG Glioma type (5-fold CV)

```
     target  n_cases  n_features  n_classes  accuracy  balanced_accuracy  macro_f1
glioma_type     1621          16          6    0.3794             0.3031    0.2581
```

## BraTS imaging — Imaging features vs PTG Site (5-fold CV)

```
target  n_cases  n_features  n_classes  accuracy  balanced_accuracy  macro_f1
  site     1621          16          5    0.6058              0.624    0.5347
```

## Extended analyses (supplementary)

### Seg volume descriptive (by glioma type / site)

```
stratify_by             level  n_cases  wt_vol_mm3_mean  et_vol_mm3_mean  et_fraction_mean
glioma_type       Astrocytoma      289     59246.200692     13301.371429          0.258298
glioma_type      Glioblastoma      882     83782.244898     13836.908676          0.162133
glioma_type        Glioma NOS      176     67911.556818     12340.011628          0.177202
glioma_type Oligodendroglioma      236     56913.694915     16545.900000          0.273070
glioma_type             Other       33     64575.909091     11105.068966          0.207455
glioma_type        glioma NOS        5     46355.800000      7157.200000          0.129297
       site              Duke      474     80975.037975     14075.379085          0.160169
       site           Indiana       31     93408.677419     14555.387097          0.174914
       site          Missouri      320     74482.253125     10803.948882          0.168776
       site              UCSD      200     80672.225000     16941.510101          0.218095
       site              UCSF      596     62950.233221     14316.795181          0.235144
```

### 2D U-Net slice Dice (exploratory; PyTorch on **py -3.12**)

```
 n_train_slices  n_val_slices  epochs  dice_wt_mean  dice_wt_std  dice_et_mean  dice_et_std                                                                          note
            250            80       6         0.125       0.3307          0.35        0.477 2D center/single-slice U-Net exploratory baseline; not nnU-Net challenge tier
```

### Subregion graph (ET/NET/edema nodes) vs glioma type

```
     target  n_cases  n_classes  balanced_accuracy  macro_f1                                                                           note
glioma_type     1621          6             0.3043    0.2655 Graph-style neighbour aggregation on 4 subregions; sklearn logistic (no torch)
```

### TCGA LGG↔GBM project holdout (log-normal AFT)

```
 n_train  n_test  c_index   amse train_project test_project         model
     512     159   0.5196 5.6513      TCGA-LGG     TCGA-GBM lognormal_aft
     159     512   0.4926 1.9538      TCGA-GBM     TCGA-LGG lognormal_aft
```

### BraTS 2024 PTG ↔ TCGA linkage report

```
{
  "crosswalk_rows": 167,
  "feature_rows": 1621,
  "overlap_ids": 0,
  "future_work": "Multimodal OS on full BraTS 2024 PTG cohort requires an official PTG\u2194TCGA crosswalk whose brats_id column matches BraTS-GLI-* in this extract."
}
```

## Reproduced vs contributed

| Component | Source |
|-----------|--------|
| deepAFT BJ/IPCW/Transform | Norman et al. 2024 |
| Covariate censoring, group scale | This dissertation |
| TCGA gene benchmark | This dissertation |
| BraTS 2024 GLI | BraTS 2024 GLI imaging features: 1621 cases; multimodal OS on full 2024 PTG cohort → future work when official crosswalk is published |
