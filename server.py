import argparse
import logging
import os

from aiohttp import web
import asyncio
import aiofiles


async def archive(request):
    archive_hash = request.match_info.get('archive_hash')
    path = f'{parser_args.path}/{archive_hash}'
    if not os.path.exists(path):
        raise web.HTTPNotFound(text='Архив не найден')

    response = web.StreamResponse(
        status=200,
        headers={
            'Content-Type': 'application/zip',
            'Content-Disposition': 'attachment; filename="archive.zip"',
        }
    )
    await response.prepare(request)

    proc = await asyncio.create_subprocess_exec(
        'zip', '-r', '-', path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    chunk_size = 64 * 1024
    try:
        while not proc.stdout.at_eof():
            chunk = await proc.stdout.read(chunk_size)
            logging.debug('Sending archive chunk ...')
            await response.write(chunk)
            await asyncio.sleep(parser_args.delay)
    finally:
        try:
            proc.kill()
            await proc.communicate()
            logging.debug('Download was interrupted')
        except ProcessLookupError:
            logging.debug('Proc has been already stopped')

    return response


async def handle_index_page(request):
    async with aiofiles.open('index.html', mode='r') as index_file:
        index_contents = await index_file.read()
    return web.Response(text=index_contents, content_type='text/html')


def create_parser():
    parser = argparse.ArgumentParser(
        description='This script is used for serving a microservice'
    )
    parser.add_argument(
        '--logs',
        default=False,
        type=bool,
        help='Set logging',
    )
    parser.add_argument(
        '--delay',
        default=0,
        type=int,
        help='Set delay between chunks are sent',
    )
    parser.add_argument(
        '--path',
        default='test_photos',
        type=str,
        help='Set source directory',
    )
    return parser


if __name__ == '__main__':
    parser = create_parser()
    parser_args = parser.parse_args()
    if parser_args.logs:
        logging.basicConfig(level=logging.DEBUG)

    app = web.Application()
    app.add_routes([
        web.get('/', handle_index_page),
        web.get('/archive/{archive_hash}/', archive),
    ])
    web.run_app(app)
