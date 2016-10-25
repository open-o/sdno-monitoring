/*
Navicat MySQL Data Transfer

Source Server         : 236
Source Server Version : 50631
Source Host           : 219.141.189.236:3306
Source Database       : topology

Target Server Type    : MYSQL
Target Server Version : 50631
File Encoding         : 65001

Date: 2016-10-26 16:46:47
*/

SET FOREIGN_KEY_CHECKS=0;

-- ----------------------------
-- Table structure for `flag`
-- ----------------------------
DROP TABLE IF EXISTS `flag`;
CREATE TABLE `flag` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `flow_add_flag` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8;

-- ----------------------------
-- Records of flag
-- ----------------------------
INSERT INTO `flag` VALUES ('1', '0');

-- ----------------------------
-- Table structure for `t_link`
-- ----------------------------
DROP TABLE IF EXISTS `t_link`;
CREATE TABLE `t_link` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `sport` int(10) unsigned NOT NULL COMMENT '源端口id，应小于目的端口id; 物理或虚拟均可',
  `dport` int(10) unsigned NOT NULL COMMENT '目的端口id, 物理或虚拟均可',
  `outAs` tinyint(1) DEFAULT NULL COMMENT '1:链接as外，0：链接as内',
  `bandwidth` float DEFAULT NULL COMMENT '带宽，Mbps',
  `unreserved_bw` float DEFAULT NULL COMMENT '未被预留的带宽，Mbps',
  PRIMARY KEY (`id`),
  KEY `sport1` (`sport`) USING BTREE,
  KEY `dport1` (`dport`) USING BTREE,
  CONSTRAINT `t_link_ibfk_1` FOREIGN KEY (`sport`) REFERENCES `t_port` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `t_link_ibfk_2` FOREIGN KEY (`dport`) REFERENCES `t_port` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=51 DEFAULT CHARSET=utf8;

-- ----------------------------
-- Records of t_link
-- ----------------------------
INSERT INTO `t_link` VALUES ('11', '1', '2', null, '10000000000', null);
INSERT INTO `t_link` VALUES ('12', '3', '26', null, '10000000000', null);
INSERT INTO `t_link` VALUES ('13', '13', '38', null, '10000000000', null);
INSERT INTO `t_link` VALUES ('14', '14', '27', null, '10000000000', null);
INSERT INTO `t_link` VALUES ('15', '15', '39', null, '10000000000', null);
INSERT INTO `t_link` VALUES ('16', '16', '28', null, '10000000000', null);
INSERT INTO `t_link` VALUES ('17', '17', '40', null, '10000000000', null);
INSERT INTO `t_link` VALUES ('18', '18', '19', null, '10000000000', null);
INSERT INTO `t_link` VALUES ('19', '20', '35', null, '10000000000', null);
INSERT INTO `t_link` VALUES ('20', '21', '47', null, '10000000000', null);
INSERT INTO `t_link` VALUES ('21', '22', '36', null, '10000000000', null);
INSERT INTO `t_link` VALUES ('22', '23', '48', null, '10000000000', null);
INSERT INTO `t_link` VALUES ('23', '24', '37', null, '10000000000', null);
INSERT INTO `t_link` VALUES ('24', '25', '49', null, '10000000000', null);
INSERT INTO `t_link` VALUES ('25', '29', '32', null, '10000000000', null);
INSERT INTO `t_link` VALUES ('26', '30', '41', null, '10000000000', null);
INSERT INTO `t_link` VALUES ('27', '31', '45', null, '10000000000', null);
INSERT INTO `t_link` VALUES ('28', '34', '46', null, '10000000000', null);
INSERT INTO `t_link` VALUES ('29', '42', '33', null, '10000000000', null);
INSERT INTO `t_link` VALUES ('30', '43', '44', null, '10000000000', null);
INSERT INTO `t_link` VALUES ('31', '2', '1', null, '10000000000', null);
INSERT INTO `t_link` VALUES ('32', '26', '3', null, '10000000000', null);
INSERT INTO `t_link` VALUES ('33', '38', '13', null, '10000000000', null);
INSERT INTO `t_link` VALUES ('34', '27', '14', null, '10000000000', null);
INSERT INTO `t_link` VALUES ('35', '39', '15', null, '10000000000', null);
INSERT INTO `t_link` VALUES ('36', '28', '16', null, '10000000000', null);
INSERT INTO `t_link` VALUES ('37', '40', '17', null, '10000000000', null);
INSERT INTO `t_link` VALUES ('38', '19', '18', null, '10000000000', null);
INSERT INTO `t_link` VALUES ('39', '35', '20', null, '10000000000', null);
INSERT INTO `t_link` VALUES ('40', '47', '21', null, '10000000000', null);
INSERT INTO `t_link` VALUES ('41', '36', '22', null, '10000000000', null);
INSERT INTO `t_link` VALUES ('42', '48', '23', null, '10000000000', null);
INSERT INTO `t_link` VALUES ('43', '37', '24', null, '10000000000', null);
INSERT INTO `t_link` VALUES ('44', '49', '25', null, '10000000000', null);
INSERT INTO `t_link` VALUES ('45', '32', '29', null, '10000000000', null);
INSERT INTO `t_link` VALUES ('46', '41', '30', null, '10000000000', null);
INSERT INTO `t_link` VALUES ('47', '45', '31', null, '10000000000', null);
INSERT INTO `t_link` VALUES ('48', '46', '34', null, '10000000000', null);
INSERT INTO `t_link` VALUES ('49', '33', '42', null, '10000000000', null);
INSERT INTO `t_link` VALUES ('50', '44', '43', null, '10000000000', null);

-- ----------------------------
-- Table structure for `t_port`
-- ----------------------------
DROP TABLE IF EXISTS `t_port`;
CREATE TABLE `t_port` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `router_id` int(10) unsigned NOT NULL,
  `type` int(10) unsigned NOT NULL COMMENT '端口是否是虚端口(多个物理端口组成一个虚端口)，0：物理端口，1：虚拟端口',
  `vport_id` int(10) unsigned DEFAULT NULL COMMENT '若此端口为物理端口,vport_id是其所属的虚拟端口id',
  `portname` varchar(30) NOT NULL,
  `capacity` int(11) DEFAULT NULL,
  `mac` varchar(17) DEFAULT NULL COMMENT '本端口对应的mac地址',
  `ip` int(11) DEFAULT NULL COMMENT '整型数的ip地址',
  `ip_str` varchar(16) DEFAULT NULL,
  `ifindex` int(11) DEFAULT '0' COMMENT '对应mib库iftable中的ifindex的值.',
  PRIMARY KEY (`id`),
  KEY `vport_id1` (`vport_id`) USING BTREE,
  KEY `router_id1` (`router_id`) USING BTREE,
  CONSTRAINT `t_port_ibfk_1` FOREIGN KEY (`vport_id`) REFERENCES `t_port` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `t_routerport_ibfk_1` FOREIGN KEY (`router_id`) REFERENCES `t_router` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=50 DEFAULT CHARSET=utf8;

-- ----------------------------
-- Records of t_port
-- ----------------------------
INSERT INTO `t_port` VALUES ('1', '1', '0', null, 'xgei-0/0/0/3', '1000', '00-00-0A-00-8C-0E', '167808014', '10.0.140.14', '0');
INSERT INTO `t_port` VALUES ('2', '2', '0', null, 'ALU   1/1/4', '1000', '00-00-0A-00-8C-0B', '167808011', '10.0.140.11', '1');
INSERT INTO `t_port` VALUES ('3', '2', '0', null, 'ALU   1/1/1', '1000', '00-00-0A-00-6F-0B', '167800587', '10.0.111.11', '2');
INSERT INTO `t_port` VALUES ('13', '2', '0', null, 'ALU   1/1/2', '1000', '00-00-0A-00-72-0B', '167801355', '10.0.114.11', '3');
INSERT INTO `t_port` VALUES ('14', '3', '0', null, 'pe12_121', '1000', '00-00-0A-00-79-0C', '167803148', '10.0.121.12', '4');
INSERT INTO `t_port` VALUES ('15', '3', '0', null, 'pe12_124', '1000', '00-00-0A-00-7C-0C', '167803916', '10.0.124.12', '5');
INSERT INTO `t_port` VALUES ('16', '4', '0', null, 'ten0/0/2/0', '1000', '00-00-0A-00-83-0D', '167805709', '10.0.131.13', '6');
INSERT INTO `t_port` VALUES ('17', '4', '0', null, 'ten0/0/2/1', '1000', '00-00-0A-00-86-0D', '167806477', '10.0.134.13', '7');
INSERT INTO `t_port` VALUES ('18', '5', '0', null, 'xgei-0/0/0/3', '1000', '00-00-0A-00-F0-18', '167833624', '10.0.240.24', '8');
INSERT INTO `t_port` VALUES ('19', '6', '0', null, 'ALU   1/1/3', '1000', '00-00-0A-00-F0-15', '167833621', '10.0.240.21', '9');
INSERT INTO `t_port` VALUES ('20', '6', '0', null, 'ALU   1/1/1', '1000', '00-00-0A-00-D5-15', '167826709', '10.0.213.21', '10');
INSERT INTO `t_port` VALUES ('21', '6', '0', null, 'ALU   1/1/2', '1000', '00-00-0A-00-D8-15', '167827477', '10.0.216.21', '11');
INSERT INTO `t_port` VALUES ('22', '7', '0', null, 'pe22_223', '1000', '00-00-0A-00-DF-16', '167829270', '10.0.223.22', '12');
INSERT INTO `t_port` VALUES ('23', '7', '0', null, 'pe22_226', '1000', '00-00-0A-00-E2-16', '167830038', '10.0.226.22', '13');
INSERT INTO `t_port` VALUES ('24', '8', '0', null, 'ten0/0/2/0', '1000', '00-00-0A-00-E9-17', '167831831', '10.0.233.23', '14');
INSERT INTO `t_port` VALUES ('25', '8', '0', null, 'ten0/0/2/1', '1000', '00-00-0A-00-EC-17', '167832599', '10.0.236.23', '15');
INSERT INTO `t_port` VALUES ('26', '9', '0', null, 'xgei-0/0/0/7', '1000', '00-00-0A-00-6F-01', '167800577', '10.0.111.1', '16');
INSERT INTO `t_port` VALUES ('27', '9', '0', null, 'xgei-0/0/0/4', '1000', '00-00-0A-00-79-01', '167803137', '10.0.121.1', '17');
INSERT INTO `t_port` VALUES ('28', '9', '0', null, 'xgei-0/0/0/6', '1000', '00-00-0A-00-83-01', '167805697', '10.0.131.1', '18');
INSERT INTO `t_port` VALUES ('29', '9', '0', null, 'xgei-0/0/0/1', '1000', '00-00-0A-00-0D-01', '167775489', '10.0.13.1', '19');
INSERT INTO `t_port` VALUES ('30', '9', '0', null, 'xgei-0/0/0/3', '1000', '00-00-0A-00-0E-01', '167775745', '10.0.14.1', '20');
INSERT INTO `t_port` VALUES ('31', '9', '0', null, 'xgei-0/0/0/2', '1000', '00-00-0A-00-10-01', '167776257', '10.0.16.1', '21');
INSERT INTO `t_port` VALUES ('32', '10', '0', null, 'xgei-0/0/0/1', '1000', '00-00-0A-00-0D-03', '167775491', '10.0.13.3', '22');
INSERT INTO `t_port` VALUES ('33', '10', '0', null, 'xgei-0/0/0/2', '1000', '00-00-0A-00-22-03', '167780867', '10.0.34.3', '23');
INSERT INTO `t_port` VALUES ('34', '10', '0', null, 'xgei-0/0/0/3', '1000', '00-00-0A-00-24-03', '167781379', '10.0.36.3', '24');
INSERT INTO `t_port` VALUES ('35', '10', '0', null, 'xgei-0/0/0/7', '1000', '00-00-0A-00-D5-03', '167826691', '10.0.213.3', '25');
INSERT INTO `t_port` VALUES ('36', '10', '0', null, 'xgei-0/0/0/4', '1000', '00-00-0A-00-DF-03', '167829251', '10.0.223.3', '26');
INSERT INTO `t_port` VALUES ('37', '10', '0', null, 'xgei-0/0/0/6', '1000', '00-00-0A-00-E9-03', '167831811', '10.0.233.3', '27');
INSERT INTO `t_port` VALUES ('38', '11', '0', null, 'xgei-0/0/0/7', '1000', '00-00-0A-00-72-04', '167801348', '10.0.114.4', '28');
INSERT INTO `t_port` VALUES ('39', '11', '0', null, 'xgei-0/0/0/4', '1000', '00-00-0A-00-7C-04', '167803908', '10.0.124.4', '29');
INSERT INTO `t_port` VALUES ('40', '11', '0', null, 'xgei-0/0/0/6', '1000', '00-00-0A-00-86-04', '167806468', '10.0.134.4', '30');
INSERT INTO `t_port` VALUES ('41', '11', '0', null, 'xgei-0/0/0/3', '1000', '00-00-0A-00-0E-04', '167775748', '10.0.14.4', '31');
INSERT INTO `t_port` VALUES ('42', '11', '0', null, 'xgei-0/0/0/2', '1000', '00-00-0A-00-22-04', '167780868', '10.0.34.4', '32');
INSERT INTO `t_port` VALUES ('43', '11', '0', null, 'xgei-0/0/0/1', '1000', '00-00-0A-00-2E-04', '167783940', '10.0.46.4', '33');
INSERT INTO `t_port` VALUES ('44', '12', '0', null, 'xgei-0/0/0/1', '1000', '00-00-0A-00-2E-06', '167783942', '10.0.46.6', '34');
INSERT INTO `t_port` VALUES ('45', '12', '0', null, 'xgei-0/0/0/2', '1000', '00-00-0A-00-10-06', '167776262', '10.0.16.6', '35');
INSERT INTO `t_port` VALUES ('46', '12', '0', null, 'xgei-0/0/0/3', '1000', '00-00-0A-00-24-06', '167781382', '10.0.36.6', '36');
INSERT INTO `t_port` VALUES ('47', '12', '0', null, 'xgei-0/0/0/7', '1000', '00-00-0A-00-D8-06', '167827462', '10.0.216.6', '37');
INSERT INTO `t_port` VALUES ('48', '12', '0', null, 'xgei-0/0/0/4', '1000', '00-00-0A-00-E2-06', '167830022', '10.0.226.6', '38');
INSERT INTO `t_port` VALUES ('49', '12', '0', null, 'xgei-0/0/0/6', '1000', '00-00-0A-00-EC-06', '167832582', '10.0.236.6', '39');

-- ----------------------------
-- Table structure for `t_router`
-- ----------------------------
DROP TABLE IF EXISTS `t_router`;
CREATE TABLE `t_router` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `site_id` int(10) unsigned DEFAULT NULL COMMENT '设备所属结点的site:site_id,若不知道，可为空',
  `name` varchar(20) DEFAULT NULL,
  `ip` int(11) DEFAULT NULL COMMENT '整型数的ip',
  `ip_str` varchar(16) DEFAULT NULL COMMENT '路由器的主ip地址',
  `community` varchar(30) DEFAULT NULL,
  `vendor` varchar(30) DEFAULT NULL COMMENT '0:华为，1：思科，2：阿朗，3：Juniper',
  `x` float DEFAULT NULL,
  `y` float DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `site_id1` (`site_id`) USING BTREE,
  CONSTRAINT `t_router_ibfk_1` FOREIGN KEY (`site_id`) REFERENCES `t_site` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=13 DEFAULT CHARSET=utf8;

-- ----------------------------
-- Records of t_router
-- ----------------------------
INSERT INTO `t_router` VALUES ('1', '1', 'beijing_pe1', '16843009', '14.14.14.14', 'ctbri', 'ZTE', '0', '150');
INSERT INTO `t_router` VALUES ('2', '1', 'beijing_p11', '33686018', '11.11.11.11', 'ctbri', 'ALU', '115', '150');
INSERT INTO `t_router` VALUES ('3', '1', 'PE12_JUNIPPER', null, '12.12.12.12', 'ctbri', 'JUNIPPER', '115', '305');
INSERT INTO `t_router` VALUES ('4', '1', 'PE13_CISCO', null, '13.13.13.13', 'ctbri', 'CISCO', '115', '460');
INSERT INTO `t_router` VALUES ('5', '2', 'shanghai_pe1', null, '24.24.24.24', 'ctbri', 'ZTE', '530', '150');
INSERT INTO `t_router` VALUES ('6', '2', 'shanghai_p11', null, '21.21.21.21', 'ctbri', 'ALU', '430', '150');
INSERT INTO `t_router` VALUES ('7', '2', 'PE22_JUNIPPER', null, '22.22.22.22', 'ctbri', 'JUNIPPER', '430', '305');
INSERT INTO `t_router` VALUES ('8', '2', 'PE23_CISCO', null, '23.23.23.23', 'ctbri', 'CISCO', '430', '460');
INSERT INTO `t_router` VALUES ('9', '3', 'beijing_p1', null, '1.1.1.1', 'ctbri', 'ZTE', '220', '225');
INSERT INTO `t_router` VALUES ('10', '3', 'shanghai_p1', null, '3.3.3.3', 'ctbri', 'ZTE', '335', '225');
INSERT INTO `t_router` VALUES ('11', '3', 'wuhan_p1', null, '4.4.4.4', 'ctbri', 'ZTE', '220', '380');
INSERT INTO `t_router` VALUES ('12', '3', 'nanjing_p1', null, '6.6.6.6', 'ctbri', 'ZTE', '335', '380');

-- ----------------------------
-- Table structure for `t_routerip`
-- ----------------------------
DROP TABLE IF EXISTS `t_routerip`;
CREATE TABLE `t_routerip` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `router_id` int(10) unsigned NOT NULL,
  `ip` int(10) unsigned NOT NULL,
  PRIMARY KEY (`id`,`ip`,`router_id`),
  KEY `router_id1` (`router_id`) USING BTREE,
  CONSTRAINT `t_routerip_ibfk_1` FOREIGN KEY (`router_id`) REFERENCES `t_router` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- ----------------------------
-- Records of t_routerip
-- ----------------------------

-- ----------------------------
-- Table structure for `t_site`
-- ----------------------------
DROP TABLE IF EXISTS `t_site`;
CREATE TABLE `t_site` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `name` varchar(50) NOT NULL COMMENT '结点名称',
  `gis_x` float DEFAULT NULL COMMENT '纬度',
  `gis_y` float DEFAULT NULL COMMENT '经度',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8;

-- ----------------------------
-- Records of t_site
-- ----------------------------
INSERT INTO `t_site` VALUES ('1', 'site_bj', '12.3', '34.3');
INSERT INTO `t_site` VALUES ('2', 'site_sh', '23.3', '56.3');
INSERT INTO `t_site` VALUES ('3', 'site_center', '35.6', '65.8');
