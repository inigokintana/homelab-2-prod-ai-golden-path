import scrapy
from scrapy.spiders import SitemapSpider


class DaprSitemapSpider(SitemapSpider):
    name = 'dapr_docs_web'
    allowed_domains = ['docs.dapr.io']
    sitemap_urls = ['https://docs.dapr.io/en/sitemap.xml']

    def parse(self, response):
        page_text = ' '.join(response.xpath('//main//text()').getall()).strip()
        yield {
            'url': response.url,
            'text': page_text
        }