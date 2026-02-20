export const PERMISSIONS = {
  VIEW_FEED: 'view_feed',
  CREATE_ARTICLE: 'create_article',
  VIEW_MY_ARTICLES: 'view_my_articles',
  ACCESS_SETTINGS: 'access_settings',
  VIEW_ADVANCED_MODE: 'view_advanced_mode',
  MANAGE_USERS: 'manage_users',
};

export const ROLE_PERMISSIONS = {
  admin: Object.values(PERMISSIONS),
  user: [PERMISSIONS.VIEW_FEED, PERMISSIONS.CREATE_ARTICLE, PERMISSIONS.VIEW_MY_ARTICLES],
};
