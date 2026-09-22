\# SatQuery AI — ChangeFormer V6 Integration Package



\## Model



Architecture:

ChangeFormerV6



Dataset:

LEVIR-CD-256



Training:

20 epochs



Optimizer:

AdamW



Learning rate:

1e-4



Weight decay:

0.01



Betas:

(0.9, 0.999)



Embed dimension:

256



Parameter count:

41,026,674



Checkpoint:

changeformer\_v6\_levir\_levircd256\_epoch20\_best.pt



Checkpoint epoch:

20



\## Inference contract



Input:

Two co-registered RGB images:

Image A = earlier image

Image B = later image



Expected image size:

256 x 256



Model call:



outputs = model(image\_A, image\_B)



The model returns 5 outputs:



1\. 8 x 8

2\. 16 x 16

3\. 32 x 32

4\. 64 x 64

5\. 256 x 256



Use:



outputs\[-1]



for final full-resolution prediction.



The output has 2 classes per pixel:



Class 0 = unchanged

Class 1 = changed



Convert logits to probabilities using:



probability = softmax(outputs\[-1], dim=1)\[:, 1, :, :]



\## Production threshold



Frozen validation threshold:



0.435



Binary change mask:



change\_mask = probability >= 0.435



IMPORTANT:

Do NOT optimize the threshold on the test set.



The threshold 0.435 was selected using the validation set and then frozen before test evaluation.



\## Final test performance



Test split:

LEVIR-CD-256 test



Samples:

2048



ROC-AUC:

0.992799529



PR-AUC:

0.927814667



F1:

0.849636270



IoU:

0.738580544



Accuracy:

0.984876938



Precision:

0.860828831



Recall:

0.838731026



Specificity:

0.992721541



Balanced accuracy:

0.915726283



These metrics are from the held-out test evaluation.



\## Important implementation rules



Do not replace the checkpoint with a synthetic or placeholder model.



Do not generate fake confidence scores.



If the checkpoint cannot be loaded, report MODEL\_CHECKPOINT\_MISSING or an equivalent explicit model-unavailable status.



The model output must come from the real ChangeFormerV6 checkpoint.



Confidence/probability should be derived from the actual model logits.



For final binary change detection, use the frozen threshold 0.435.



\## Checkpoint verification



Expected architecture:

ChangeFormerV6



Expected embed\_dim:

256



Expected parameters:

41,026,674



The supplied checkpoint was successfully loaded with:



load\_state\_dict(strict=True)



with:



missing\_keys = \[]

unexpected\_keys = \[]



\## Evidence



reports/validation\_final\_report.json

reports/frozen\_validation\_threshold.json

reports/final\_test\_report.json

reports/qualitative\_final\_report.json



These reports contain the actual validation/test evaluation results.

