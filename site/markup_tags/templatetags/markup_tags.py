from django import template
import markdown
from docutils.core import publish_parts

register = template.Library()

class MarkdownNode(template.Node):
    def __init__(self, nodelist):
        self.nodelist = nodelist

    def render(self, context):
        output = self.nodelist.render(context)
        return markdown.markdown(output)

@register.tag('markdown')
def do_markdown(parser, token):
    nodelist = parser.parse(('endmarkdown',))
    parser.delete_first_token()
    return MarkdownNode(nodelist)

class RestructuredNode(template.Node):
    def __init__(self, nodelist):
        self.nodelist = nodelist

    def render(self, context):
        output = self.nodelist.render(context)
        return publish_parts(source=output,
             writer_name='html4css1',
             settings_overrides={'initial_header_level': 3})['fragment']

@register.tag('rest')
def do_rest(parser, token):
    nodelist = parser.parse(('endrest',))
    parser.delete_first_token()
    return RestructuredNode(nodelist)
