// @ts-check
// `@type` JSDoc annotations allow editor autocompletion and type checking
// (when paired with `@ts-check`).
// See: https://docusaurus.io/docs/api/docusaurus-config

/** @type {import('@docusaurus/types').Config} */
const config = {
  title: 'falk',
  tagline: 'Governed AI access to your data warehouse, powered by semantic layers.',
  favicon: 'img/logo.png',

  url: 'https://fredehagelund92.github.io',
  baseUrl: '/Falk/',

  organizationName: 'Fredehagelund92',
  projectName: 'Falk',

  onBrokenLinks: 'throw',

  markdown: {
    hooks: {
      onBrokenMarkdownLinks: 'warn',
    },
  },

  staticDirectories: ['docs/static'],

  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  presets: [
    [
      'classic',
      /** @type {import('@docusaurus/preset-classic').Options} */
      ({
        docs: {
          path: 'docs',
          routeBasePath: '/',
          sidebarPath: './sidebars.js',
          editUrl: 'https://github.com/Fredehagelund92/Falk/tree/main/',
          showLastUpdateTime: false,
        },
        blog: false,
        theme: {
          customCss: './docs/custom.css',
        },
      }),
    ],
  ],

  themeConfig:
    /** @type {import('@docusaurus/preset-classic').ThemeConfig} */
    ({
      navbar: {
        logo: {
          alt: 'falk',
          src: 'img/logo.png',
        },
        items: [
          {
            type: 'docSidebar',
            sidebarId: 'docsSidebar',
            position: 'left',
            label: 'Docs',
          },
          {
            href: 'https://github.com/Fredehagelund92/Falk',
            label: 'GitHub',
            position: 'right',
          },
        ],
      },
      prism: {
        additionalLanguages: ['bash', 'yaml', 'json'],
      },
      colorMode: {
        defaultMode: 'light',
        disableSwitch: true,
      },
    }),

  trailingSlash: false,
};

module.exports = config;
