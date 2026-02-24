/**
 * Create as many sidebars as you need.
 *
 * @see https://docusaurus.io/docs/sidebar
 */

/** @type {import('@docusaurus/plugin-content-docs').SidebarsConfig} */
const sidebars = {
  docsSidebar: [
    'index',
    {
      type: 'category',
      label: 'Getting Started',
      collapsed: false,
      items: [
        'getting-started/quickstart',
        'getting-started/installation',
        'getting-started/mcp',
        'cli',
      ],
    },
    {
      type: 'category',
      label: 'Concepts',
      items: [
        'concepts/how-it-works',
        'concepts/state',
        'concepts/memory',
        'concepts/metric-decomposition',
        'concepts/context-engineering',
        'concepts/tools',
      ],
    },
    {
      type: 'category',
      label: 'Configuration',
      items: [
        'configuration/index',
        'configuration/semantic-models',
        'configuration/metric-relationships',
        'configuration/agent',
        'configuration/llm-providers',
        'configuration/tuning',
      ],
    },
    {
      type: 'category',
      label: 'Deployment',
      items: [
        'deployment/slack',
        'deployment/web-ui',
        'deployment/logfire',
      ],
    },
    {
      type: 'category',
      label: 'Advanced',
      items: [
        'concepts/evals',
        'concepts/learning',
      ],
    },
    {
      type: 'category',
      label: 'Reference',
      items: [
        'cli-reference',
        'reference/where-syntax',
      ],
    },
    'contributing',
  ],
};

module.exports = sidebars;
