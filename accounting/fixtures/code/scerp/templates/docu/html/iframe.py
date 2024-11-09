from docutils import nodes
from docutils.parsers.rst import roles

def iframe_role(name, rawtext, text, lineno, inliner, options={}, content=[]):
    return [nodes.raw('', '<iframe src="{}" width="100%" height="1200px" frameborder="0"></iframe>'.format(text), format='html')], []

def setup(app):
    roles.register_local_role('iframe', iframe_role)
