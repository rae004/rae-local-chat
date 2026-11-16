from mcp.types import (
    BlobResourceContents,
    ContentBlock,
    EmbeddedResource,
    ImageContent,
    TextContent,
    TextResourceContents,
)

from rae_api.services.mcp import flatten_content


def test_text_blocks_join_with_newlines() -> None:
    blocks = [TextContent(type="text", text="a"), TextContent(type="text", text="b")]
    assert flatten_content(blocks) == "a\nb"


def test_text_resource_passes_its_text_through() -> None:
    # GitHub's get_file_contents: a text block with a summary, then the file as a resource.
    blocks: list[ContentBlock] = [
        TextContent(type="text", text="successfully downloaded text file"),
        EmbeddedResource(
            type="resource",
            resource=TextResourceContents(
                uri="repo://o/r/contents/README.md",
                mime_type="text/markdown",
                text="# README\n",
            ),
        ),
    ]
    assert flatten_content(blocks) == "successfully downloaded text file\n# README\n"


def test_binary_resource_and_image_are_marked_not_dumped() -> None:
    blocks: list[ContentBlock] = [
        EmbeddedResource(
            type="resource",
            resource=BlobResourceContents(
                uri="repo://o/r/contents/logo.png", mime_type="image/png", blob="AAAA"
            ),
        ),
        ImageContent(type="image", data="AAAA", mime_type="image/png"),
    ]
    out = flatten_content(blocks)
    assert "AAAA" not in out
    assert out == "[binary resource repo://o/r/contents/logo.png omitted]\n[image content omitted]"
