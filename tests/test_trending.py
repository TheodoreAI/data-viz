from unittest import TestCase
from unittest.mock import Mock, patch

import trending


class FetchArxivTests(TestCase):
    @patch('trending.requests.get')
    def test_fetches_most_cited_computer_science_papers_from_arxiv(self, get):
        response = Mock()
        response.json.return_value = {
            'results': [{
                'display_name': 'Adam: A Method for Stochastic Optimization',
                'publication_year': 2014,
                'cited_by_count': 83533,
                'primary_topic': {'display_name': 'Stochastic Gradient Optimization Techniques'},
                'locations': [{
                    'landing_page_url': 'http://arxiv.org/abs/1412.6980',
                    'source': {'id': 'https://openalex.org/S4306400194'},
                }],
            }],
        }
        get.return_value = response

        items = trending.fetch_arxiv(page=3)

        response.raise_for_status.assert_called_once_with()
        _, kwargs = get.call_args
        self.assertEqual(kwargs['params']['sort'], 'cited_by_count:desc')
        self.assertEqual(kwargs['params']['page'], 3)
        self.assertIn('primary_topic.field.id:17', kwargs['params']['filter'])
        self.assertEqual(items, [{
            'title': 'Adam: A Method for Stochastic Optimization',
            'description': 'Stochastic Gradient Optimization Techniques',
            'citations': 83533,
            'year': 2014,
            'url': 'https://arxiv.org/abs/1412.6980',
        }])

    @patch('trending.requests.get')
    def test_skips_results_without_an_arxiv_abstract_link(self, get):
        response = Mock()
        response.json.return_value = {
            'results': [{
                'display_name': 'Journal-only result',
                'locations': [{
                    'landing_page_url': 'https://example.com/paper',
                    'source': {'id': 'https://openalex.org/S123'},
                }],
            }],
        }
        get.return_value = response

        self.assertEqual(trending.fetch_arxiv(), [])

    def test_builds_arxiv_url_from_repository_identifier(self):
        locations = [{
            'id': 'pmh:oai:arXiv.org:1603.02754',
            'landing_page_url': 'https://doi.org/10.48550/arxiv.1603.02754',
            'source': {'id': 'https://openalex.org/S4306400194'},
        }]

        self.assertEqual(
            trending._arxiv_url(locations),
            'https://arxiv.org/abs/1603.02754',
        )

    def test_converts_arxiv_pdf_link_to_abstract_link(self):
        locations = [{
            'landing_page_url': 'http://export.arxiv.org/pdf/1502.03167',
            'source': {'id': 'https://openalex.org/S4306400194'},
        }]

        self.assertEqual(
            trending._arxiv_url(locations),
            'https://arxiv.org/abs/1502.03167',
        )
