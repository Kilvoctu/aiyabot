import os
import sys
import argparse
import asyncio
from src.core.logging import get_logger
from src.bot.shanghai import Shanghai

logger = get_logger(__name__)

def parse_args():
    parser = argparse.ArgumentParser(
        description='Shanghai - A Discord bot for AI powered utilities.',
        usage='shanghai [arguments]'
    )

    parser.add_argument('--prefix', type=str, help='The prefix to use for commands.', default='s!')
    parser.add_argument('--token', type=str, help='The token to use for authentication.')
    parser.add_argument('--hf_token', type=str, help='The token to use for HuggingFace authentication.', default=None)
    parser.add_argument('--model_path', type=str, help='Path to the model.', default=None)

    return parser.parse_args()

async def shutdown(bot):
    await bot.close()

def main():
    shanghai = None
    args = parse_args()
    
    try:
        shanghai = Shanghai(args)
        logger.info('Executing bot.')
        shanghai.run(args.token)
    except KeyboardInterrupt:
        logger.info('Keyboard interrupt received. Exiting.')
        asyncio.run(shutdown(shanghai))
    except SystemExit:
        logger.info('System exit received. Exiting.')
        asyncio.run(shutdown(shanghai))
    except Exception as e:
        logger.error(e)
        asyncio.run(shutdown(shanghai))
    finally:
        sys.exit(0)

if __name__ == '__main__':
    main()