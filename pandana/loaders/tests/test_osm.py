import pytest

from pandana.loaders import osm


@pytest.fixture(scope='module')
def bbox():
    return 37.8659303546, -122.2588003879, 37.8661598571, -122.2585062512


@pytest.fixture(scope='module')
def query_data(bbox):
    return osm.make_osm_query(*bbox)


def test_make_osm_query(query_data):
    assert isinstance(query_data, dict)
    assert len(query_data['elements']) == 37
    assert len(
        [e for e in query_data['elements'] if e['type'] == 'node']) == 33
    assert len([e for e in query_data['elements'] if e['type'] == 'way']) == 4


def test_process_node():
    test_node = {
        'id': 'id',
        'lat': 'lat',
        'lon': 'lon',
        'extra': 'extra'
    }

    expected = {
        'id': 'id',
        'lat': 'lat',
        'lon': 'lon'
    }

    assert osm.process_node(test_node) == expected

    test_node['tags'] = {'highway': 'highway', 'source': 'source'}
    expected['highway'] = 'highway'

    assert osm.process_node(test_node) == expected


def test_process_way():
    test_way = {
        "type": "way",
        "id": 188434143,
        "timestamp": "2014-01-04T22:18:14Z",
        "version": 2,
        "changeset": 19814115,
        "user": "dchiles",
        "uid": 153669,
        "nodes": [
            53020977,
            53041093,
        ],
        "tags": {
            'source': 'source',
            "addr:city": "Berkeley",
            "highway": "secondary",
            "name": "Telegraph Avenue",
        }
    }

    expected_way = {
        'id': test_way['id'],
        'addr:city': test_way['tags']['addr:city'],
        'highway': test_way['tags']['highway'],
        'name': test_way['tags']['name']
    }

    expected_waynodes = [
        {'way_id': test_way['id'], 'node_id': test_way['nodes'][0]},
        {'way_id': test_way['id'], 'node_id': test_way['nodes'][1]}
    ]

    way, waynodes = osm.process_way(test_way)

    assert way == expected_way
    assert waynodes == expected_waynodes


def test_parse_osm_query(query_data):
    nodes, ways, waynodes = osm.parse_osm_query(query_data)

    assert len(nodes) == 33
    assert len(ways) == 4
    assert len(waynodes.index.unique()) == 4
