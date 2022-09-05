module.exports = {
  packagerConfig: {
    extraResource: [
      'tmp/resources/alpha',
      'tmp/resources/beta'
    ],
    ignore: [
      /^\/build(\/|$)/,
      /^\/tmp(\/|$)/,
      /^\/icon\.icns$/,
      /^\/forge\.config\.js$/
    ],
    name: 'PR–1',
    icon: 'icon.icns'
  },
  makers: [
    { name: '@electron-forge/maker-zip' }
  ]
}
