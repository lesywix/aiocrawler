#!/usr/bin/env python3
import asyncio
import sys
import time
from urllib.parse import urlparse, urljoin, urldefrag
import logging

from bs4 import BeautifulSoup
import aiohttp
import click


def fix_url(url):
    if '://' not in url:
        url = 'https://' + url
    return url


class AIOCrawler(object):
    def __init__(self, root_url, loop, concurrency):
        self.root_url = root_url
        self.root_domain = '{uri.scheme}://{uri.netloc}/'.format(uri=urlparse(self.root_url))
        self.seen_urls = set()
        self.ok_result = set()
        self.failed_result = set()

        self.queue = asyncio.Queue(loop=loop)
        self.session = aiohttp.ClientSession(loop=loop)
        self.loop = loop
        self.queue.put_nowait((self.root_url, None))  # init queue with (root_url, parent_url/None)
        self.concurrency = concurrency
        self.logger = logging.getLogger('AIOCrawler')

    async def crawl(self):
        self.logger.info('Start crawler...')
        workers = [self.loop.create_task(self.work(i)) for i in range(self.concurrency)]
        await self.queue.join()
        for w in workers:
            w.cancel()
        await self.close()

    async def work(self, worker_id):
        self.logger.debug(f'Start worker {worker_id}')
        try:
            while True:
                url, parent_url = await self.queue.get()
                await self.fetch_html(url, parent_url)
                self.queue.task_done()
        except asyncio.CancelledError:
            pass

    async def fetch_html(self, url, parent_url):
        try:
            async with self.session.get(url) as response:
                if response.status < 400:
                    self.logger.debug(f'Get url: <{url}> successful, parent url: <{parent_url}>')
                    self.ok_result.add((response.url, parent_url))
                    if response.content_type == 'text/html':
                        html = await response.text()
                        await self.parse_links(response.url, html)
                else:
                    self.logger.debug(f'Get url: <{url}> failed, parent url: <{parent_url}>')
                    self.failed_result.add((url, parent_url))

        except Exception as e:
            self.logger.exception(f'Exception: {e}')

    async def parse_links(self, parent_url, html):
        """parse link from html and return unseen urls"""
        soup = BeautifulSoup(html, features='html.parser')
        urls = [a.get('href', '') for a in soup.find_all('a', href=True)]
        urls += [a.get('src', '') for a in soup.find_all('img')]
        urls = set([urldefrag(urljoin(str(parent_url), u))[0] for u in urls[:]])
        unseen_urls = urls.difference(self.seen_urls)
        for u in unseen_urls:
            if u not in self.seen_urls and u.startswith(self.root_url):
                await self.queue.put((u, parent_url))
                self.seen_urls.add(u)

    async def close(self):
        self.logger.info('Close session')
        await self.session.close()


@click.command()
@click.argument('root_url')
@click.option('-v', help='Show ok-links', is_flag=True)
@click.option('-c', '--concurrency', default=20, show_default=True, help='Concurrency of crawler')
@click.option('-vv', help='Show debug info', is_flag=True)
def main(root_url, v, concurrency, vv):
    """Simple link scanner to detect broken links"""
    click.echo(f'Start scanning: {root_url}')

    root_url = fix_url(root_url)
    logging.basicConfig(level=logging.DEBUG) if vv else logging.basicConfig(level=logging.INFO)
    loop = asyncio.get_event_loop()
    crawler = AIOCrawler(root_url, loop, concurrency)
    try:
        t0 = time.time()
        loop.run_until_complete(crawler.crawl())
        click.echo(f'duration: {time.time() - t0}')
    except KeyboardInterrupt:
        for t in asyncio.Task.all_tasks():
            t.cancel()
        sys.stderr.flush()
        click.echo(click.style('\nExit crawler\n', fg='red'))

    finally:
        click.echo(f'total links: {len(crawler.seen_urls)}')
        click.echo(click.style(f'   - ok: {len(crawler.ok_result)}', fg='green'))
        if v:
            for i in crawler.ok_result:
                click.echo(click.style(f'       - {i[0]}', fg='green'))
        click.echo(click.style(f'   - failed: {len(crawler.failed_result)}', fg='yellow'))
        for i in crawler.failed_result:
            click.echo(click.style(f'       - {i[0]}; parent_link: {i[1]}', fg='yellow'))

        loop.close()


if __name__ == '__main__':
    main()
