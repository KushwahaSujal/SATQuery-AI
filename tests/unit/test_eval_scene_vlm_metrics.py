from scripts.eval_scene_vlm_vrsbench import rouge_l, vqa_correct, vqa_strict_correct


def test_vqa_correct_normalises_case_punctuation_and_articles():
    assert vqa_correct("Yellow.", "yellow")
    assert vqa_correct("The buses are yellow.", "Yellow")
    assert not vqa_correct("Red", "yellow")
    assert not vqa_correct("yellowish", "yellow")


def test_rouge_l_bounds():
    assert rouge_l("a b c", "a b c") == 1.0
    assert rouge_l("", "a") == 0.0
    assert 0.0 < rouge_l("large yellow buses parked", "a group of large yellow buses") < 1.0


def test_vqa_strict_correct_exact_match_after_normalisation():
    assert vqa_strict_correct("Yellow.", "yellow")


def test_vqa_strict_correct_rejects_verbose_answer_even_if_it_contains_the_word():
    assert not vqa_strict_correct("The buses are yellow.", "yellow")


def test_vqa_strict_correct_rejects_negated_word():
    assert not vqa_strict_correct("not yellow", "yellow")


def test_vqa_strict_correct_exact_number_match():
    assert vqa_strict_correct("2", "2")


def test_vqa_strict_correct_rejects_number_buried_in_a_sentence():
    assert not vqa_strict_correct("There are 2 or 3 buildings", "2")
