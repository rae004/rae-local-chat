# Changelog

## [0.1.1](https://github.com/rae004/rae-local-chat/compare/v0.1.0...v0.1.1) (2026-10-25)


### Bug Fixes

* **frontend:** truncate long chat titles in the sidebar ([#13](https://github.com/rae004/rae-local-chat/issues/13)) ([f6127e4](https://github.com/rae004/rae-local-chat/commit/f6127e43fb517d2136b3a8988b888b44fd15ad87))

## 0.1.0 (2026-10-25)


### Features

* **api:** /models from Ollama tags, per-request model on stream ([2ec3f59](https://github.com/rae004/rae-local-chat/commit/2ec3f59651116d77007205485b97faf90da11c42))
* **api:** chat rename/delete, title autogen, activity ordering ([e3996ef](https://github.com/rae004/rae-local-chat/commit/e3996efbee25ebc416a9b9535e41dd193202f805))
* **api:** fastapi app, chats router, echo endpoint, tests ([ac93fa7](https://github.com/rae004/rae-local-chat/commit/ac93fa760378302f1fef84141fc112e6c9b74a97))
* **api:** SSE streaming endpoint proxying Ollama /api/chat ([2220666](https://github.com/rae004/rae-local-chat/commit/22206663f62a12e2ed0204f3e27cd29a7ead3349))
* **db:** models + alembic init migration ([f5c09eb](https://github.com/rae004/rae-local-chat/commit/f5c09eb04cb5c637ecfbc2b370bf83f6cf7039a5))
* **frontend:** consume SSE stream with useChatStream ([d6a95fe](https://github.com/rae004/rae-local-chat/commit/d6a95fea097aa12e9debaa1e348d895848b7c1e2))
* **frontend:** rename/delete chats in sidebar, Rae Bot branding ([d8810f0](https://github.com/rae004/rae-local-chat/commit/d8810f04c4c7e154a75fa359b4f8515892ed5de2))
* **frontend:** theme toggle, model selector, markdown rendering ([fa3a36d](https://github.com/rae004/rae-local-chat/commit/fa3a36d1c0d490eafef5e1a4d6838fd766e3b74e))
* **frontend:** vite+react+router+query scaffold, sidebar + prompt box ([f8376e0](https://github.com/rae004/rae-local-chat/commit/f8376e07ff287849ccafef221e54b888b476e1c9))


### Bug Fixes

* **api:** shield partial-reply persist from request cancellation ([34c1136](https://github.com/rae004/rae-local-chat/commit/34c1136efc929f8bd541b680d271611df79191ca))

## Changelog
