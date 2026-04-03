from jinja2 import Environment

env = Environment(autoescape=True)
template = env.from_string("const todosPombos = {{ data | tojson | safe if data else '[]' }};")

print("With empty list:", template.render(data=[]))
print("With null:", template.render(data=None))
print("With data:", template.render(data=[{"n": 1}]))
