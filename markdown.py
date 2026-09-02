import mistune

from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter

class HighlightRenderer(mistune.HTMLRenderer):
    def block_code(self, code, info=None):
        if info:
            try:
                lexer = get_lexer_by_name(info, stripall=True)
                formatter = HtmlFormatter()
                return highlight(code, lexer, formatter)
            except Exception:
                return '<pre><code>' + mistune.escape(code) + '</code></pre>'
        return '<pre><code>' + mistune.escape(code) + '</code></pre>'

    def image(self, alt, url, title=None):
        return (
            '<small class="figure">'
                + super().image(alt, url, title=title)
                + f'<span class="caption">{alt}</span>'
            + '</small>')

markdown = mistune.create_markdown(
    hard_wrap=False,
    renderer=HighlightRenderer(),
    plugins=["strikethrough", "footnotes", "table", "math", "spoiler"]
)
markdown_ast = mistune.create_markdown(renderer='ast')

def collect_images(raw_markdown):
    images = set()

    tokens = markdown_ast(raw_markdown)
    stk = list(reversed(tokens))
    while stk:
        token = stk.pop()
        if token['type'] == 'image':
            images.add(token['attrs']['url'])

        if 'children' in token:
            for child in reversed(token['children']):
                stk.append(child)
    return images
