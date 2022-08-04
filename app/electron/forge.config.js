module.exports = {
  packagerConfig: {
    extraResource: [
      'tmp/host'
    ],
    ignore: [
      /^tmp$/
    ],
    name: 'PR–1'
  },
  makers: [
    { name: '@electron-forge/maker-dmg' },
    { name: '@electron-forge/maker-zip',
      platforms: ['darwin', 'linux'] },
    { name: '@electron-forge/maker-squirrel',
      config: {
        authors: 'LBNC',
        description: 'Protocol Runner 1'
      } }
  ]
}
