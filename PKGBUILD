# Maintainer: Felipe Ruhland <archlinux@feliperuhland.com>

pkgname=cdf-shell
pkgver=0.1.0
pkgrel=1
pkgdesc="Interactively search the directory tree below the cwd and cd into the result"
arch=('any')
url="https://github.com/feliperuhland/cdf-shell"
license=('MIT')
depends=('python' 'fzf')
makedepends=('python-build' 'python-hatchling' 'python-installer')
checkdepends=('python-pytest')
_pkgsrc="${pkgname}-${pkgver}"
source=("${pkgname}-${pkgver}.tar.gz::${url}/archive/v${pkgver}.tar.gz")
# Placeholder — v${pkgver} isn't tagged upstream yet, so this can't be computed
# for real. Run `updpkgsums` once it is; this deliberately fails checksum
# verification (rather than using SKIP) so makepkg refuses to build silently
# unverified.
sha256sums=('0000000000000000000000000000000000000000000000000000000000000000')

build() {
  cd "${_pkgsrc}"
  python -m build --wheel --no-isolation
}

check() {
  cd "${_pkgsrc}"
  python -m venv --system-site-packages test-env
  test-env/bin/python -m installer dist/*.whl
  test-env/bin/python -m pytest -o addopts="" tests/
}

package() {
  cd "${_pkgsrc}"
  python -m installer --destdir="${pkgdir}" dist/*.whl

  install -vDm644 README.md "${pkgdir}/usr/share/doc/${pkgname}/README.md"
  install -vDm644 LICENSE "${pkgdir}/usr/share/licenses/${pkgname}/LICENSE"
}
