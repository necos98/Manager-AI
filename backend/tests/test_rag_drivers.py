from unittest.mock import MagicMock, patch


def test_sentence_transformer_dimension():
    from app.rag.drivers.sentence_transformer import SentenceTransformerDriver
    with patch("app.rag.drivers.sentence_transformer.SentenceTransformer") as mock_cls:
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_cls.return_value = mock_model
        driver = SentenceTransformerDriver(model_name="all-MiniLM-L6-v2")
        assert driver.dimension == 384


def test_sentence_transformer_embed():
    from app.rag.drivers.sentence_transformer import SentenceTransformerDriver
    with patch("app.rag.drivers.sentence_transformer.SentenceTransformer") as mock_cls:
        import numpy as np
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_model.encode.return_value = np.random.rand(2, 384).astype(np.float32)
        mock_cls.return_value = mock_model
        driver = SentenceTransformerDriver(model_name="all-MiniLM-L6-v2")
        result = driver.embed(["hello", "world"])
        assert len(result) == 2
        assert len(result[0]) == 384
        mock_model.encode.assert_called_once_with(["hello", "world"], batch_size=32)


def test_sentence_transformer_lazy_loading():
    from app.rag.drivers.sentence_transformer import SentenceTransformerDriver
    with patch("app.rag.drivers.sentence_transformer.SentenceTransformer") as mock_cls:
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_cls.return_value = mock_model
        driver = SentenceTransformerDriver(model_name="all-MiniLM-L6-v2")
        # Constructor should NOT load the model yet
        mock_cls.assert_not_called()
        # Accessing dimension triggers loading
        _ = driver.dimension
        mock_cls.assert_called_once_with("all-MiniLM-L6-v2")
