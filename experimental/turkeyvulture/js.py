import sys
import jsonjinja
from jsonjinja.utils import get_runtime_javascript


# env = jsonjinja.Environment(loader=jsonjinja.DictLoader({
#     'results': '''\
# <div>
# {% if person.length %}
# <h2>Legislators ({{ person_count }})</h2>
# <ul>
# {% for leg in person %}
#     <li>
#     <div class='content'>
#     <i class='icon-user'></i>
#     <h3>
#         [{{leg.chamber}}] <a href='http://openstates.org/{{leg.state}}/legislators/{{leg._id}}/'>{{ leg.full_name }}</a>
#     </h3> ({{leg.party}}--{{leg.district}})
#     </div>
#     </li>
# {% endfor %}
# </ul>
# {% else %}
#  <h2>No Legislators Found</h2>
# {% endif %}

# {#
# {% if person.length %}
#     {% for leg in person %}
#     <li>
#     <i class='icon-user'></i>
#     <div class='content'>
#     <h3>{{ leg.full_name }}</h3> ({{leg.party}}--{{leg.district}})
#     <div class="row-fluid">
#         {% for role in leg.roles %}
#             {% if role.committee %}
#                 <div class="span4">{{role.committee}}</div>
#             {% endif %}
#         {% endfor %}
#     </div>
#     </div>
#     </li>
#     {% endfor %}
# {% endif %}
# #}


# {% if committee %}
# <h2>Committees ({{ committee_count }})</h2>
# <ul>
# {% for c in committee %}
#     <div class='content'>
#     <i class='icon-lock'></i>
#     <li><h3>
#         [{{c.chamber}}]
#         <a href='http://openstates.org/{{c.state}}/committees/{{c._id}}/'>{{ c.committee }}</a>
#     </h3></li>
#     </div>
# {% endfor %}
# </ul>
# {% else %}
#  <h2>No Committees Found</h2>
# {% endif %}

# {% if bill %}
# <h2>Bills ({{ bill_count }})</h2>
# <ul>
# {% for b in bill %}
#     <li>
#         <div class='content'>
#         <i class='icon-file'></i>
#         <h3>
#             <a href='http://openstates.org/{{b.state}}/bills/{{b.session}}/{{b.bill_id}}'>
#             {{ b.bill_id }}
#             </a>
#         </h3>
#         <p>{{ b.title }}</p>
#         </div>
#         <p>
#         {% for subject in b.type %}
#             <span class='label'>{{ subject }}</span>
#         {% endfor %}
#         {% for subject in b.subjects %}
#             <span class='label'>{{ subject }}</span>
#         {% endfor %}
#         {% for subject in b.scraped_subjects %}
#             <span class='label'>{{ subject }}</span>
#         {% endfor %}
#         </p>
#     </li>
# {% endfor %}
# </ul>
# </div>
# {% else %}
#  <h2>No Bills Found</h2>
# {% endif %}
# '''}))


loader = jsonjinja.FileSystemLoader('templates')
env = jsonjinja.Environment(loader=loader)

print get_runtime_javascript()
print 'jsonjinja.addTemplates('
env.compile_javascript_templates(stream=sys.stdout)
print ');'
# print 'document.write(jsonjinja.getTemplate("test.html").render({seq: ["cow", 2, 33, "pig"], title: "Jab"}));'
