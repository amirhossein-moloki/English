from src.media.base import MediaProvider, ImageProvider


def test_media_abstractions():
    class DummyImageProvider(ImageProvider):
        @property
        def name(self) -> str:
            return "dummy_image"

        @property
        def is_available(self) -> bool:
            return True

        def get_image(self, item):
            return None

    provider = DummyImageProvider()
    assert provider.name == "dummy_image"
    assert provider.media_type == "image"
    assert provider.is_available is True
