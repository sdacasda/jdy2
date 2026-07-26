include $(TOPDIR)/rules.mk

PKG_NAME:=athena-runtime
PKG_VERSION:=19.0.0
PKG_RELEASE:=1

include $(INCLUDE_DIR)/package.mk

define Package/athena-runtime
  SECTION:=utils
  CATEGORY:=Utilities
  TITLE:=Athena AX6600 safe runtime and recovery tools
  DEPENDS:=+jshn +jsonfilter +rpcd +ucode +curl +ca-bundle +tar +gzip
endef

define Package/athena-runtime/description
 Safe setup, DAED templates, IoT Wi-Fi compatibility, health checks,
 verified backup and rollback for JDCloud RE-CS-02.
endef

define Build/Compile
endef

define Package/athena-runtime/install
	$(INSTALL_DIR) $(1)/
	$(CP) ./files/* $(1)/
	chmod 0755 \
		$(1)/usr/bin/athena-* \
		$(1)/etc/init.d/athena-runtime \
		$(1)/usr/libexec/rpcd/athena
endef

$(eval $(call BuildPackage,athena-runtime))
