import os
import shutil
import click
import subprocess
from configparser import ConfigParser, ExtendedInterpolation
from urllib.parse import urlparse


class TurmyxConfig(ConfigParser):
    DIR_PATH = os.path.dirname(os.path.realpath(__file__))

    def __init__(self):
        self.config_path = os.path.join(self.DIR_PATH, "configuration.ini")
        super(TurmyxConfig, self).__init__(interpolation=ExtendedInterpolation())
        self.read(self.config_path)

    def guess_file_command(self, file):
        assert isinstance(file, str)
        assert isinstance(self, ConfigParser)

        file_name = os.path.basename(file)
        extension = file_name.split('.')[-1]

        for section in self.sections():
            if "default" not in section and "editor" in section:
                if extension in self[section]["extensions"].split(" "):
                    return section

        return "editor:default"

    def guess_url_command(self, url):
        assert isinstance(url, str)
        assert isinstance(self, ConfigParser)

        url_parsed = urlparse(url)
        domain = url_parsed.netloc

        if not domain:
            print("Failed to parse URL. Attempt default opener.")
            return "opener:default"

        for section in self.sections():
            if "default" not in section and "opener" in section:
                print(section)
                if domain in self[section]["domains"].split(" "):
                    return section

        return "opener:default"


turmyx_config_context = click.make_pass_decorator(TurmyxConfig, ensure=True)


@click.group(invoke_without_command=True)
@turmyx_config_context
def cli(config_ctx):
    """
    This is turmyx! A script launcher for external files/url in Termux. Enjoy!
    """
    # config_ctx.read(config_ctx.config_path)
    # click.echo(click.get_current_context().get_help())
    pass


@cli.command()
@click.option('--merge',
              'mode',
              flag_value='merge',
              help="Merge new file config into the existing file.")
@click.option('--symlink',
              'mode',
              flag_value='symlink',
              help="Symlink to the provided configuration file.")
@click.option('--view',
              is_flag=True,
              help="Output the actual configuration of Turmyx scripts.")
@click.argument('file',
                type=click.Path(exists=True),
                required=False,
                )
@turmyx_config_context
def config(config_ctx, file, mode, view):
    """
    Set configuration file.

    You can use a mode flag to configure how to save the new configuration. Both can't be combined, so the last one
    to be called will be the used by the config command.
    """

    if file:

        os.remove(config_ctx.config_path)

        abs_path = os.path.abspath(file)
        click.echo("Absolute path for provided file: {}".format(abs_path))

        new_config = TurmyxConfig()
        new_config.read(abs_path)

        # TODO: validate this config file.

        if not mode:
            with open(config_ctx.config_path, "w") as config_f:
                new_config.write(config_f)
            click.echo("Succesfully saved into {}.".format(config_ctx.config_path))
        elif mode == "merge":
            # First attempt, only overriding partials:

            config_ctx.read(abs_path)
            with open(config_ctx.config_path, "w") as config_f:
                config_ctx.write(config_f)
            click.echo("Succesfully merged: {} \n into: {} \n and saved.".format(abs_path, config_ctx.config_path))

        elif mode == "symlink":
            os.symlink(abs_path, config_ctx.config_path)
            click.echo("Succesfully linked: {} \n to: {}.".format(config_ctx.config_path, abs_path))

    if view:
        with open(config_ctx.config_path, 'r') as config_f:
            click.echo(config_f.read())


@cli.command()
@click.argument('file',
                type=click.Path(exists=True),
                required=False,
                )
@turmyx_config_context
def editor(config_ctx, file):
    """
    Run suitable editor for any file in Termux.

    You can soft-link this command with:

    ln -s ~/bin/termux-file-editor $PREFIX/bin/turmyx-file-editor
    """
    if isinstance(file, str):
        section = config_ctx.guess_file_command(file)
        command = config_ctx[section]["command"]

        try:
            if "command_args" in section:
                arguments = config_ctx[section]["command_args"]
                call_args = [command] + arguments.split(" ") + [file]
            else:
                call_args = [command, file]

            click.echo(" ".join(call_args))
            subprocess.check_call(call_args)

        except FileNotFoundError:
            click.echo("'{}' not found. Please check the any typo or installation.".format(command))


@cli.command()
@click.argument('url',
                type=str,
                required=False,
                )
@turmyx_config_context
def opener(config_ctx, url):
    """
    Run suitable parser for any url in Termux.

    You can soft-link this command with:

    ln -s ~/bin/termux-url-opener $PREFIX/bin/turmyx-url-opener
    """
    if isinstance(url, str):
        section = config_ctx.guess_url_command(url)
        command = config_ctx[section]["command"]

        try:
            if "command_args" in section:
                arguments = config_ctx[section]["command_args"]
                call_args = [command] + arguments.split(" ") + [url]
            else:
                call_args = [command, url]

            click.echo(" ".join(call_args))
            subprocess.check_call(call_args)

        except FileNotFoundError:
            click.echo("'{}' not found. Please check the any typo or installation.".format(command))


@cli.command()
@click.argument('mode',
                type=str,
                nargs=1,
                )
@click.option('--name',
              type=str,
              nargs=1,
              help='A name for the script configuration, otherwise it will be guessed from script path.'
              )
@click.option('--default',
              is_flag=True,
              help='The script will be saved as default one for the given mode, --name option and any argument in '
                   'CASES_LIST would be ignored.'
              )
@click.argument('script',
                type=str,
                required=True)
@click.argument('cases_list',
                type=str,
                nargs=-1,
                required=False,
                )
@turmyx_config_context
def add(config_ctx, script, mode, cases_list, name, default):
    """
    Add a new script configuration.

    Examples:

        turmyx add editor nano txt md ini

        turmyx add --name radare editor r2 exe

        turmyx add opener youtube-dl youtube.com youtu.be

        turmyx add --default opener qr


    Adds a new script to Turmyx, the configuration is setted inline by an OPTION --name, otherwhise the name is
    guessed from script name. The argument MODE has to be 'editor' or 'opener' and sets the run environment of the
    script. SCRIPT must be a valid path to the script/program, and must be executable, otherwise when executing it
    would lead to an exception. Finally, the CASES_LIST will contain a list of extensions or domains to be used along with the script.

    """

    if mode not in ("opener", "editor"):
        click.echo("{} is not 'opener' or 'editor' mode.".format(mode))
        return

    click.echo("Evaluating script: {}".format(script))

    script_path = shutil.which(script)

    if script_path:
        script_path = os.path.abspath(script_path)
        click.echo("Absolute path found for script: {}".format(script_path))
    else:
        click.echo("Given script not found or not executable.")
        return

    basename = os.path.basename(script_path)

    if not default:
        section = "{}:{}".format(mode, name if name else basename)
    else:
        section = "{}:default".format(mode)

    config_ctx[section] = {}
    args_command = [section, "command", script_path]
    config_ctx.set(*args_command)

    if cases_list and not default:
        args_cases = [section, "extensions" if mode == "editor" else "domains", ' '.join(cases_list)]
        config_ctx.set(*args_cases)

    with open(config_ctx.config_path, "w") as config_f:
        config_ctx.write(config_f)


@cli.command()
@click.argument('script',
                type=str,
                required=True)
@turmyx_config_context
def remove(config_ctx, script):
    """
    Removes script configuration.
    """
    if config_ctx.remove_section(script):
        click.echo("Script configuration successfully removed!")

        with open(config_ctx.config_path, 'w') as config_f:
            config_ctx.write(config_f)
    else:
        click.echo("Configuration not found.")
        section_guesses = []
        for section in config_ctx.sections():
            if script in section:
                section_guesses.append(section)

        if section_guesses:
            click.echo("Maybe you want to say:\n{}".format(
                "\n".join(section_guesses)
            ))

