from shorts_pipeline.models import Source, Topic
from shorts_pipeline.publish import metadata
from shorts_pipeline.seo import fallback_package


def test_fallback_package_preserves_source_url():
    source = Source("A breakthrough", "https://example.test/source", "A useful finding.")
    package = fallback_package(Topic("A breakthrough", "AI", (source,)))
    assert source.url in package.description
    assert package.sources == [source.url]


def test_metadata_is_platform_neutral():
    source = Source("A breakthrough", "https://example.test/source", "A useful finding.")
    data = metadata(fallback_package(Topic("A breakthrough", "AI", (source,))))
    assert set(data) == {"title", "description", "tags", "sources"}
