import ckan.plugins as plugins
import ckan.logic as logic
import ckan.plugins.toolkit as tk
import csv
import os
import json
from ckan.common import OrderedDict, _, json, request, c, g, response
import ckan.model as model
import datetime
from shapely.geometry import asShape
from pylons import config
import logging
log = logging.getLogger(__name__)

def custom_output_validator(key, data, errors, context):
    value = data.get(key)
    value = value.replace('{', '').replace('}', '').replace(',"', ', ').replace('"', '').replace(',', ', ')
    data[key] = value

def custom_output_validator_theme(key, data, errors, context):
    value = data.get(key)
    value = value.replace('[', '').replace(']', '').replace("u'", '').replace("'", '').replace(',', ', ').replace('{', '').replace('}', '')
    data[key] = value

def get_group_select_list():
    result = []
    user = tk.get_action('get_site_user')({'ignore_auth': True}, {})
    context = {'user': user['name']}
    groups = logic.get_action('group_list')(context, {})

    for group in groups:
        result.append({'value': group})
    return result

def group_id():
    id =  request.params.get('group') or request.params.get('groups__0__id')
    return id

# vocab setup
# "Geospatial Topic" and "Field(s) of Research" are tag vocabularies.
def create_geospatial_topics():
    user = tk.get_action('get_site_user')({'ignore_auth': True}, {})
    context = {'user': user['name']}
    vocab = model.Vocabulary.get('geospatial_topics')
    if not vocab:
        data = {'name': 'geospatial_topics'}
        vocab = tk.get_action('vocabulary_create')(context, data)
        for tag in ('Farming', 'Biota', 'Boundaries', 'Climatology Meteorology and Atmosphere', 'Economy', 'Elevation',
                    'Environment',
                    'Geoscientific information', 'Health', 'Imagery base maps and Earth cover',
                    'Intelligence and Military',
                    'Inland waters', 'Location', 'Oceans', 'Planning and Cadastre', 'Society', 'Transportation',
                    'Utilities and Communication'):
            data = {'name': tag, 'vocabulary_id': vocab['id']}
            tk.get_action('tag_create')(context, data)


def geospatial_topics():
    create_geospatial_topics()
    try:
        tag_list = tk.get_action('tag_list')
        geospatial_topics = tag_list(data_dict={'vocabulary_id': 'geospatial_topics'})
        return geospatial_topics
    except tk.ObjectNotFound:
        return None

def groups():
    query = model.Group.all(group_type='group')

    def convert_to_dict(user):
        out = {}
        for k in ['id', 'name', 'title']:
            out[k] = getattr(user, k)
        return out

    out = map(convert_to_dict, query.all())
    return out


def create_fields_of_research():

    user = tk.get_action('get_site_user')({'ignore_auth': True}, {})
    context = {'user': user['name']}
    vocab = model.Vocabulary.get('fields_of_research')
    if not vocab:
        print "Loading ABS Fields of Research for the first time, please wait..."
        data = {'name': 'fields_of_research'}
        vocab = tk.get_action('vocabulary_create')(context, data)
        with open(os.path.dirname(os.path.abspath(__file__)) + '/ABS Fields Of Research.csv', 'rb') as csvfile:
            forcsv = csv.reader(csvfile)
            for row in forcsv:
                data = {'name': row[1].strip().replace(',', '')[:100], 'vocabulary_id': vocab['id']}
                tk.get_action('tag_create')(context, data)
        print "ABS Fields of Research loaded"


def fields_of_research():
    create_fields_of_research()
    try:
        tag_list = tk.get_action('tag_list')
        fields_of_research = tag_list(data_dict={'vocabulary_id': 'fields_of_research', 'all_fields': False})
        return fields_of_research
    except tk.ObjectNotFound:
        return None

def delete_fields_theme():
    user = tk.get_action('get_site_user')({'ignore_auth': True}, {})
    context = {'user': user['name']}
    vocab = model.Vocabulary.get('fields_theme')
    if vocab:
        log.info("Found Fields Theme, please wait...")
        data = {'id': vocab.id}
        vocab = tk.get_action('vocabulary_delete')(context, data)
        log.info("Success delete vocab")

def delete_tags_fields_theme():
    user = tk.get_action('get_site_user')({'ignore_auth': True}, {})
    context = {'user': user['name']}
    vocab = model.Vocabulary.get('fields_theme')
    tag_list = tk.get_action('tag_list')
    fields_theme = tag_list(data_dict={'vocabulary_id': 'fields_theme'})
    log.info('fields_theme_tags = %s, type = %s', fields_theme, type(fields_theme))
    for tag in fields_theme:
        data = {'id': tag, 'vocabulary_id': vocab.id}
        tk.get_action('tag_delete')(context, data)
        log.info('tag_delete = %s', data)
        log.info('tag = %s, type = %s, vocab = %s', tag, type(tag), vocab.id)


def create_fields_theme():
    user = tk.get_action('get_site_user')({'ignore_auth': True}, {})
    context = {'user': user['name']}
    vocab = model.Vocabulary.get('fields_theme')
    if not vocab:
        log.info("Loading Fields Theme for the first time, please wait...")
        data = {'name': 'fields_theme'}
        vocab = tk.get_action('vocabulary_create')(context, data)
        log.info("Success create vocab")
        for tag in groups():
            data = {'name': tag['title'], 'vocabulary_id': vocab['id']}
            tk.get_action('tag_create')(context, data)
            log.info('tag_create = %s', data)

def fields_theme():
    #create_fields_theme()
    #delete_tags_fields_theme()
    #delete_fields_theme()
    out = []
    for tag in groups():
        out.append(tag['title'])
    return out
    """
    try:
        tag_list = tk.get_action('tag_list')
        fields_theme = tag_list(data_dict={'vocabulary_id': 'fields_theme', 'all_fields': False})
        log.info('tag_list = %s, type = %s', fields_theme, type(fields_theme))
        return fields_theme
    except tk.ObjectNotFound:
        return None"""    


def spatial_bound(spatial_str):
    if spatial_str and spatial_str != '':
        spatial_dict = json.loads(spatial_str)
        return asShape(spatial_dict).bounds
    return None

def get_user_full(username):
    try:
        return plugins.toolkit.get_action('user_show')({'return_minimal': True, 'keep_sensitive_data': True, 'keep_email': True},{'id': username})
    except plugins.toolkit.ObjectNotFound:
        return None
def get_org_full(id):
        try:
            return plugins.toolkit.get_action('organization_show')({'include_datasets': False},{'id': id})
        except plugins.toolkit.ObjectNotFound:
            return None
def is_site(site_name):
    result = site_name in config.get('ckan.site_url', '')
    return result
def get_now():
    return datetime.datetime.now().strftime('%Y-%M-%d')


def iso_languages_list():
    return config.get('iso638.2')

class AGLSDatasetPlugin(plugins.SingletonPlugin,
                        tk.DefaultDatasetForm):
    '''An example IDatasetForm CKAN plugin.

    Uses a tag vocabulary to add a custom metadata field to datasets.

    '''
    plugins.implements(plugins.IConfigurer, inherit=False)
    # plugins.implements(plugins.IDatasetForm, inherit=False)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IRoutes, inherit=True)
    plugins.implements(plugins.IValidators)

    def before_map(self, map):
        map.connect('/dataset/{id}/gmd',
                    controller='ckanext.agls.controller:AGLSController', action='gmd')
        map.connect('/api/2/util/gazetteer/autocomplete',
                    controller='ckanext.agls.controller:AGLSController', action='geo_autocomplete')
        map.connect('/api/2/util/gazetteer/latlon',
                    controller='ckanext.agls.controller:AGLSController', action='geo_latlon')
        return map

    def get_helpers(self):
        return {'fields_of_research': fields_of_research,
                'geospatial_topics': geospatial_topics,
                'fields_theme': fields_theme,
                'get_group_select_list': get_group_select_list,
                'spatial_bound': spatial_bound,
                'get_user_full': get_user_full,
                'get_org_full': get_org_full,
                'groups': groups, 'group_id': group_id,
                'is_site': is_site, 'get_now': get_now,
                'iso_languages_list': iso_languages_list}

    def get_validators(self):
        return { 'custom_output_validator': custom_output_validator,
                 'custom_output_validator_theme': custom_output_validator_theme }            

    def update_config(self, config):
        # Add this plugin's templates dir to CKAN's extra_template_paths, so
        # that CKAN will use this plugin's custom templates.
        # here = os.path.dirname(__file__)
        # rootdir = os.path.dirname(os.path.dirname(here))

        tk.add_template_directory(config, 'templates')
        tk.add_public_directory(config, 'theme/public')
        tk.add_public_directory(config, 'fanstatic/ckanext-agls')
        tk.add_resource('fanstatic', 'ckanext-agls')

        here = os.path.dirname(__file__)

        with open(os.path.join(here, 'languages.json')) as languages:
            config['iso638.2'] = json.load(languages)
        # config['licenses_group_url'] = 'http://%(ckan.site_url)/licenses.json'

    # def is_fallback(self):
    #     # Return True to register this plugin as the default handler for
    #     # package types not handled by any other IDatasetForm plugin.
    #     return True

    # def package_types(self):
    #     # This plugin doesn't handle any special package types, it just
    #     # registers itself as the default (above).
    #     return []


    # def create_package_schema(self):
    #     schema = super(AGLSDatasetPlugin, self).create_package_schema()
    #     schema = self._modify_package_schema(schema)
    #     return schema

    # def update_package_schema(self):
    #     schema = super(AGLSDatasetPlugin, self).update_package_schema()
    #     schema = self._modify_package_schema(schema)
    #     return schema

    # def show_package_schema(self):
    #     schema = super(AGLSDatasetPlugin, self).show_package_schema()

    #     # Don't show vocab tags mixed in with normal 'free' tags
    #     # (e.g. on dataset pages, or on the search page)
    #     schema['tags']['__extras'].append(tk.get_converter('free_tags_only'))

    #     # Add our custom_text field to the dataset schema.
    #     # ignore_missing == optional
    #     # ignore_empty == mandatory but not for viewing
    #     # !!! always convert_from_extras first
    #     schema.update({

    #         'contact_point': [tk.get_converter('convert_from_extras'),
    #                           tk.get_validator('ignore_empty')],
    #         'contact_info': [tk.get_converter('convert_from_extras'),
    #                          tk.get_validator('ignore_missing')],
    #         'unpublished': [tk.get_converter('convert_from_extras'),
    #                          tk.get_validator('ignore_missing')],
    #         'spatial_coverage': [tk.get_converter('convert_from_extras'),
    #                              tk.get_validator('ignore_empty')],
    #         'spatial': [tk.get_converter('convert_from_extras'),
    #                     tk.get_validator('ignore_empty')],
    #         'jurisdiction': [tk.get_converter('convert_from_extras'),
    #                          tk.get_validator('ignore_empty')],
    #         'temporal_coverage_from': [tk.get_converter('convert_from_extras'),
    #                                    tk.get_validator('ignore_empty')],
    #         'temporal_coverage_to': [tk.get_converter('convert_from_extras'),
    #                                  tk.get_validator('ignore_missing')],
    #         'data_state': [tk.get_converter('convert_from_extras'),
    #                        tk.get_validator('ignore_empty')],
    #         'update_freq': [tk.get_converter('convert_from_extras'),
    #                         tk.get_validator('ignore_empty')],
    #         'data_model': [tk.get_converter('convert_from_extras'),
    #                        tk.get_validator('ignore_missing')],
    #         'language': [tk.get_converter('convert_from_extras'),
    #                        tk.get_validator('ignore_missing')],
    #         'geospatial_topic': [
    #             tk.get_converter('convert_from_tags')('geospatial_topics'),
    #             tk.get_validator('ignore_missing')],
    #         'field_of_research': [
    #             tk.get_converter('convert_from_tags')('fields_of_research'),
    #             tk.get_validator('ignore_missing')],
    #         # harvesting fields
    #          'spatial_harvester': [tk.get_converter('convert_from_extras'),
    #          tk.get_validator('ignore_missing')],
    #          'harvest_object_id': [tk.get_converter('convert_from_extras'),
    #                            tk.get_validator('ignore_missing')],
    #         'harvest_source_id': [tk.get_converter('convert_from_extras'),
    #                            tk.get_validator('ignore_missing')],
    #         'harvest_source_title': [tk.get_converter('convert_from_extras'),
    #                            tk.get_validator('ignore_missing')]
    #     })
    #     return schema

    # def _modify_package_schema(self, schema):
    #     # Add our custom_test metadata field to the schema, this one will use
    #     # convert_to_extras instead of convert_to_tags.
    #     # ignore_missing == optional
    #     # not_empty == mandatory, enforced here while modifying

    #     schema.update({
    #         'contact_point': [tk.get_converter('convert_to_extras'),
    #                           tk.get_validator('not_empty')],
    #         'contact_info': [tk.get_validator('ignore_missing'),
    #                          tk.get_converter('convert_to_extras')],
    #         'unpublished': [tk.get_validator('ignore_missing'),
    #                          tk.get_converter('convert_to_extras')],
    #         'spatial_coverage': [tk.get_converter('convert_to_extras'),
    #                              tk.get_validator('not_empty')],
    #         'spatial': [tk.get_validator('ignore_missing'),
    #                     tk.get_converter('convert_to_extras')],
    #         'jurisdiction': [tk.get_converter('convert_to_extras'),
    #                          tk.get_validator('not_empty')],
    #         'temporal_coverage_from': [tk.get_converter('convert_to_extras'),
    #                                    tk.get_validator('not_empty')],
    #         'temporal_coverage_to': [tk.get_validator('ignore_missing'),
    #                                  tk.get_converter('convert_to_extras')],
    #         'data_state': [tk.get_converter('convert_to_extras'),
    #                        tk.get_validator('not_empty')],
    #         'update_freq': [tk.get_converter('convert_to_extras'),
    #                         tk.get_validator('not_empty')],
    #         'data_models': [tk.get_validator('ignore_missing'),
    #                         tk.get_converter('convert_to_extras')],
    #         'language': [tk.get_validator('ignore_missing'),
    #                         tk.get_converter('convert_to_extras')],
    #         'geospatial_topic': [
    #             tk.get_validator('ignore_missing'),
    #             tk.get_converter('convert_to_tags')('geospatial_topics')
    #         ],
    #         'field_of_research': [
    #             tk.get_validator('ignore_missing'),
    #             tk.get_converter('convert_to_tags')('fields_of_research')
    #         ],
    #         # harvesting fields
    #          'spatial_harvester': [tk.get_validator('ignore_missing'),
    #          tk.get_converter('convert_to_extras')],
    #          'harvest_object_id': [tk.get_validator('ignore_missing'),
    #                            tk.get_converter('convert_to_extras')],
    #         'harvest_source_id': [tk.get_validator('ignore_missing'),
    #                            tk.get_converter('convert_to_extras')],
    #         'harvest_source_title': [tk.get_validator('ignore_missing'),
    #                            tk.get_converter('convert_to_extras')],

    #     })
    #     return schema
#
