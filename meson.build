project('universal-java-installer', version: '1.0.0', meson_version: '>=0.59.0')

datadir = get_option('prefix') / get_option('datadir')
appdir = datadir / 'universal-java-installer'

subdir('po')
subdir('polkit')

install_subdir('src', install_dir: appdir)

install_data(
    'data/io.github.ruysabino.JavaInstaller.svg',
    install_dir: datadir / 'icons/hicolor/scalable/apps',
)
install_data(
    'data/io.github.ruysabino.JavaInstaller.desktop',
    install_dir: datadir / 'applications',
)
install_data(
    'data/io.github.ruysabino.JavaInstaller.metainfo.xml',
    install_dir: datadir / 'metainfo',
)
install_data(
    'universal-java-installer',
    install_dir: get_option('prefix') / get_option('bindir'),
    install_mode: 'rwxr-xr-x',
)
