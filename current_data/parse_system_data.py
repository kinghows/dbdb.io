#!/usr/bin/env python

import os
import sys
import json

import django
from django.utils import timezone
from django.utils.text import slugify

sys.path.append("..")
from systems import util
os.environ['DJANGO_SETTINGS_MODULE'] = 'website.settings'
django.setup()

sys_file = '../systems/fixtures/systems.json'
sys_ver_file = '../systems/fixtures/system_versions.json'

fixtures_dir = '../systems/fixtures/'
fixtures = os.listdir(fixtures_dir)
fixtures = [fixtures_dir + x for x in fixtures]

# Exclude systems.json and system_versions.json.
for filename in [sys_file, sys_ver_file]:
    try:
        fixtures.remove(filename)
    except:
        # File missing.
        pass

# Printed out after script is finished
print_output = {}


# Add print output based on filename and category
def add_print_output(filename, category, output):
    if not print_output.get(filename):
        print_output[filename] = {}
    if not print_output[filename].get(category):
        print_output[filename][category] = []
    print_output[filename][category].append(output)

# Create a map of field->name->pk.
# pk = Primary Key

pk_map = {}
"""
Get primary keys and names from fixtures and put in pk_map.

pk_map: {
    "oses": {
        "server-less": 19,
        "HP-UX": 8,
        ...
    },
    "written_in": {
        "Javascript": 24,
        "Java": 22,
        ...
    },
    "license": {
        Public Domain": 13,
        "LGPL": 7,
        ...
    }
    "feature": {
        "Query Execution": 13,
        "Logging": 10,
        ...
    },
    "feature_options-13": {
        "Vectorized Model": 2,
        "Tuple-at-a-Time Model": 1,
        ...
    },
    ...
}
"""

# Read each fixture and store the primary key
for fixture in fixtures:
    with open(fixture, 'r') as fd:
        data = json.loads(fd.read())
        for datum in data:
            model = datum['model']
            if model == 'systems.FeatureOption':
                field = 'feature_options-' + str(datum['fields']['feature'])
                entries = pk_map.get(field, {})
                entries[datum['fields']['value']] = datum['pk']
                pk_map[field] = entries
            elif model == 'systems.Feature':
                field = 'feature'
                entries = pk_map.get(field, {})
                entries[datum['fields']['label']] = datum['pk']
                pk_map[field] = entries
            elif model == 'systems.License':
                field = 'licenses'
                entries = pk_map.get(field, {})
                entries[datum['fields']['name']] = datum['pk']
                pk_map[field] = entries
            elif model == 'systems.OperatingSystem':
                field = 'oses'
                entries = pk_map.get(field, {})
                entries[datum['fields']['name']] = datum['pk']
                pk_map[field] = entries
            elif model == 'systems.ProgrammingLanguage':
                field = 'written_in'
                entries = pk_map.get(field, {})
                entries[datum['fields']['name']] = datum['pk']
                pk_map[field] = entries
            elif model == 'systems.ProjectType':
                field = 'project_type'
                entries = pk_map.get(field, {})
                entries[datum['fields']['name']] = datum['pk']
                pk_map[field] = entries
            else:
                add_print_output("All", "Unsupported Fixture", 'Skipping ' + model + ' with pk: ' + datum['pk'])

add_print_output("All", "Primary Key Map", pk_map)


def map_to_pk(fields, field, values, key, filename):
    """
    Map names in values under a field to primary keys. Append to existing fields in the fixture.
    ex. fields = { ... license: [1, 2] ... } field = 'license', values = ['MIT'], filename = foo.json
    result = [1, 2, 8]
    """
    result = fields.get(field, [])
    for value in values:
        try:
            result.append(pk_map[field][value])
        except KeyError:
            add_print_output(filename, "Incorrect Value", 'Could not map \'' + value + '\' from ' + key + ' in ' + filename +
                             ' to any models under \'' + field + '\'')
    return result


# Map of fields in json files to system_version fields
system_map = {
    'Name': 'name',
    'Description': 'description',
    'Email': 'creator',
    'Developer': 'developer',
    'History': 'history',
    'Licenses': 'licenses',
    'Website': 'website',
    'Programming Language': 'written_in',
    'Operating Systems': 'oses',
    'Project Type': 'project_type',
    'Start Date': 'start_year',
    'End Date': 'end_year',
     # TODO Not formatted correctly in the json files
     # 'Derived From': 'derived_from'
}


systems = {}  # models.System
system_versions = []  # models.SystemVersion
pk = 1


# Read json files and convert to fixtures
def create_fixtures(directory, files):
    global pk, systems, system_versions
    for filename in files:
        with open(directory + '/' + filename, 'r') as infile:
            try:
                data = json.loads(infile.read())
            except Exception as error:
                add_print_output(directory + '/' + filename, "Other", 'Could not read ' + directory + '/' + filename + ' ' + str(error))
                continue

            # TODO This is a temporary hotfix for files with Name or Website as a list
            if isinstance(data.get('Name'), list) and len(data['Name']) >= 1:
                data['Name'] = data['Name'][0]
            if isinstance(data.get('Website'), list) and len(data['Website']) >= 1:
                data['Website'] = data['Website'][0]

            # Skip systems with existing name.
            if systems.get(data['Name']):
                continue

            slug = slugify(data['Name'])
            repeat_slugs = 0
            for sys in systems.itervalues():
                if sys['fields']['slug'] == slug:
                    repeat_slugs += 1

            if repeat_slugs != 0:
                slug += str(repeat_slugs)

            sys_fixture = {
                'pk': pk,
                'model': 'systems.System',
                'fields': {
                    'name': data['Name'],
                    'slug': slug,
                    'created': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'secret_key': util.generateSecretKey()
                }
            }

            fields = {}

            # Copy each compatible field from the json object to the model
            for key, value in system_map.iteritems():
                try:
                    field_value = data[key]
                    if isinstance(field_value, list):
                        # Skip many to many values
                        continue
                    if value in pk_map:
                        # Assign primary key values
                        fields[value] = pk_map[value][field_value]
                    else:
                        # Assign other types of value.
                        fields[value] = data[key]
                except KeyError as error:
                    add_print_output(directory + '/' + filename, "Missing Key", 'Could not find ' + str(error) + ' key in ' + directory + '/' + filename)

            # Copy over remaining values to model
            for key, value in data.iteritems():
                if 'Citation' in key:
                    # Citations not yet handled
                    continue
                elif ' Description' in key:
                    # Descriptions of feature options
                    field = 'description_' + key[:-12].replace(' ', '').lower()
                    fields[field] = value
                elif ' Options' in key:
                    # try:
                    # Copy over options to model
                    field = 'support_' + key[:-8].replace(' ', '').lower()
                    if len(value) > 0 and value[0] != 'Not Supported' and value[0] != 'N/A':
                        # Is supported
                        fields[field] = True
                        field = 'options_' + key[:-8].replace(' ', '').lower()
                        pk_field = 'feature_options-' + str(pk_map['feature'][key[:-8]])
                        fields[field] = map_to_pk(fields, pk_field, value, key, directory + '/' + filename)
                    elif len(value) > 0 and value[0] == 'Not Supported':
                        fields[field] = False
                    else:
                        fields[field] = None
                    # except Exception as error:
                    #     print value
                    #     add_print_output(filename, "Incorrect Value", str(error))
                elif isinstance(value, list):
                    # Some type of list, use the pk_map
                    field = system_map.get(key, None)
                    if field is not None:
                        fields[field] = map_to_pk(fields, field, value, key, directory + '/' + filename)
                elif system_map.get(key, None) is None or fields.get(system_map[key], None) is None:
                    # Not a list and not in system_map
                    add_print_output(directory + '/' + filename, "Missing Key",
                                     'Could not map \'' + key + '\' in ' + directory + '/' + filename + ' to any models')

            fields['system'] = pk
            fields['created'] = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
            sys_ver_fixture = {
                'pk': pk,
                'model': 'systems.SystemVersion',
                'fields': fields
            }
            systems[data['Name']] = sys_fixture
            system_versions.append(sys_ver_fixture)
        pk += 1


# Write the fixtures to a file
def write_fixtures():
    with open(sys_file, 'w') as outfile1, open(sys_ver_file, 'w') as outfile2:
        mycmp = lambda x, y: cmp(x['pk'], y['pk'])

        systems_list = list(systems.itervalues())
        systems_list.sort(cmp=mycmp)
        outfile1.write(json.dumps(systems_list, indent=4))

        system_versions.sort(cmp=mycmp)
        outfile2.write(json.dumps(system_versions, indent=4))


create_fixtures('spring2016', os.listdir('spring2016'))
create_fixtures('spring2017', os.listdir('spring2017'))
create_fixtures('data', os.listdir('data'))
create_fixtures('json_data', os.listdir('json_data'))
write_fixtures()

with open('system_data_output.txt', 'w') as output_file:
    output_file.write(json.dumps(print_output, indent=4))
    print 'Errors can be found in system_data_output.txt'
