from scripts.eval_scene_vlm_vrsbench import rouge_l, vqa_correct


def test_vqa_correct_normalises_case_punctuation_and_articles():
    assert vqa_correct("Yellow.", "yellow")
    assert vqa_correct("The buses are yellow.", "Yellow")
    assert not vqa_correct("Red", "yellow")
    assert not vqa_correct("yellowish", "yellow")


def test_rouge_l_bounds():
    assert rouge_l("a b c", "a b c") == 1.0
    assert rouge_l("", "a") == 0.0
    assert 0.0 < rouge_l("large yellow buses parked", "a group of large yellow buses") < 1.0
