# Re-export from backend.app.models.cdvqa_model for training scripts
from backend.app.models.cdvqa_model import (
    CDVQAModel,
    ChangeEnhancingModule,
    TextQuestionEncoder,
    CDVQA_ANSWER_CLASSES,
    ANSWER2IDX,
    IDX2ANSWER,
    VOCAB_WORDS,
    WORD2IDX,
    tokenize_question
)
