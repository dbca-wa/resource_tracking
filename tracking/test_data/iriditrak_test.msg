Return-Path: bl+SRS=fF1u5=KR=sbd.iridium.com=sbdservice@list.fms.wa.gov.au
Delivered-To: tracking@mail.lan.fyi
X-FDA: 81882926622.05.8CC6EBF
Received: from SY2PR01CU004.outbound.protection.outlook.com
 (mail-australiaeastazon11021019.outbound.protection.outlook.com
 [52.101.150.19])
	by imf28.hostedemail.com (Postfix) with ESMTP id AA277C0006
	for <tracking@mail.lan.fyi>; Mon, 11 Mar 2024 00:50:08 +0000 (UTC)
Authentication-Results: imf28.hostedemail.com;
	dkim=pass header.d=DPaW.onmicrosoft.com
 header.s=selector1-DPaW-onmicrosoft-com header.b=b9dIUofE;
	arc=pass ("microsoft.com:s=arcselector9901:i=1");
	dmarc=none;
	spf=pass (imf28.hostedemail.com: domain of
 "bl+SRS=fF1u5=KR=sbd.iridium.com=sbdservice@list.fms.wa.gov.au" designates
 52.101.150.19 as permitted sender)
 smtp.mailfrom="bl+SRS=fF1u5=KR=sbd.iridium.com=sbdservice@list.fms.wa.gov.au"
ARC-Seal: i=2; s=arc-20220608; d=hostedemail.com; t=1710118208; a=rsa-sha256;
	cv=pass;
	b=UIhsMlbmQpcgV3U2wcGcOM+WHEdq4LXVg3bPN5VvIr7fojdpMNSVVlgPMNFGqrYPKEiymE
	oGKvvPXMUJpxkb266fzB2MmR4AE7iefbMKBgUN31ZsMEyL0wVxuM4RDrvrnh7Wgz+qKV3o
	VzQE6IjeoNeC/03Z1HT7mliLzevt1wE=
ARC-Authentication-Results: i=2;
	imf28.hostedemail.com;
	dkim=pass header.d=DPaW.onmicrosoft.com
 header.s=selector1-DPaW-onmicrosoft-com header.b=b9dIUofE;
	arc=pass ("microsoft.com:s=arcselector9901:i=1");
	dmarc=none;
	spf=pass (imf28.hostedemail.com: domain of
 "bl+SRS=fF1u5=KR=sbd.iridium.com=sbdservice@list.fms.wa.gov.au" designates
 52.101.150.19 as permitted sender)
 smtp.mailfrom="bl+SRS=fF1u5=KR=sbd.iridium.com=sbdservice@list.fms.wa.gov.au"
ARC-Message-Signature: i=2; a=rsa-sha256; c=relaxed/relaxed;
 d=hostedemail.com;
	s=arc-20220608; t=1710118208;
	h=from:from:sender:reply-to:reply-to:subject:subject:date:date:
	 message-id:message-id:to:to:cc:mime-version:mime-version:
	 content-type:content-type:content-transfer-encoding:resent-from:
	 in-reply-to:references:dkim-signature;
	bh=fhFYdetL3mZiak110kyiHLmKCgX/oUKNkL37DvQzopE=;
	b=AmZ0ala2+c3AudWGb8e5gV2HwaKp+J+weOjYa0s/h1OHEVZVPkzCf5J3NzjNE65Kj3ERlv
	AiI+51vfpOcZgluQfUDRR18pyh0/vRIBozgqKt9Pcf0CLzv7c8J161dmG8QulzxIvdzYnR
	zFVmTBr94ZY6Wim3aO6KnUrfIQZYU3Y=
ARC-Seal: i=1; a=rsa-sha256; s=arcselector9901; d=microsoft.com; cv=none;
 b=aRoGNyieDTcRfu2gRlXERx+tdRP5HkvXZAfyB4XbVSC5DoWsdXub+JH9Ae7zrBpFRqs7jph0Spvqx7Aap3sz1x4WwN7cXJWjFPaYChgJ1NfbeQeadx7ltIWmzYyBuDprum+WaqgCUO9MmL/sABTSZcgZUOucyOfQiN9M8jR5m/rUOkkbFjBrtfO7oQ1CqTAkhQ7xhBztv/fap4hX2FT+RQRFjfl7N6iZmCLrWqmvdoUGE24Hkx8mfoxg62b3xtv4cqrEhC/V5eAxg8Ibs3TEACZWnB0mn7p69SDs2vGb5JmvKoUI73rJ+/Vx4lewM0QcYY5INsF3uMNnAwpzJH5kfQ==
ARC-Message-Signature: i=1; a=rsa-sha256; c=relaxed/relaxed; d=microsoft.com;
 s=arcselector9901;
 h=From:Date:Subject:Message-ID:Content-Type:MIME-Version:X-MS-Exchange-AntiSpam-MessageData-ChunkCount:X-MS-Exchange-AntiSpam-MessageData-0:X-MS-Exchange-AntiSpam-MessageData-1;
 bh=fhFYdetL3mZiak110kyiHLmKCgX/oUKNkL37DvQzopE=;
 b=h2tflpf0cKM1rFNA0hfDc2RIA6G8igubwX3v/fZAKFP/vDBZAF5FWE+W3CPvBosx8BdfHFlEVPjDTLoEEgU+QHir0DziLPwEUHPln8zuxmoJeDM+lYR/6ELxyBndh0WIPBxfUVQKu0Nid8ymvgiiclmlM53XxK/GfNo3BcUxtp+L2ude7gszlwLQrAz180mMfTsxEHiE6XiHnennXWLEUjMmADHqVz/O484XqSy+KAlt+RDz3PYFFffnctJxVSKNt+3TOOTYMCeSygXQe6C6DhPoJL3izUlOJRN/56AocozqO8rX6EF5iWIphteXd8/8OImugZ49zj1bxttTn4UH1w==
ARC-Authentication-Results: i=1; mx.microsoft.com 1; spf=pass (sender ip is
 12.47.179.11) smtp.rcpttodomain=list.fms.wa.gov.au
 smtp.mailfrom=sbd.iridium.com; dmarc=bestguesspass action=none
 header.from=sbd.iridium.com; dkim=none (message not signed); arc=none (0)
DKIM-Signature: v=1; a=rsa-sha256; c=relaxed/relaxed; d=DPaW.onmicrosoft.com;
 s=selector1-DPaW-onmicrosoft-com;
 h=From:Date:Subject:Message-ID:Content-Type:MIME-Version:X-MS-Exchange-SenderADCheck;
 bh=fhFYdetL3mZiak110kyiHLmKCgX/oUKNkL37DvQzopE=;
 b=b9dIUofE6tqnZRplRvdEBmKMqBf7LMWroIHGVc9ZvwTWHaPTnraPXT8HWeL/m0IeJDeHraXLV7On22iqHZuKHv4EBUJrtwryj8tXx7PQ7SJX9AalyRleNad/oBCLfCaEs3Xx0VrjghTk/dzX4fWZYo+g5V1drvglN3f/+UbrThc=
Resent-From: <bl@list.fms.wa.gov.au>
Received: from SYBPR01CA0177.ausprd01.prod.outlook.com (2603:10c6:10:52::21)
 by ME3PR01MB8244.ausprd01.prod.outlook.com (2603:10c6:220:1b4::8) with
 Microsoft SMTP Server (version=TLS1_2,
 cipher=TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384) id 15.20.7362.34; Mon, 11 Mar
 2024 00:50:04 +0000
Received: from SY1PEPF00005A3F.ausprd01.prod.outlook.com
 (2603:10c6:10:52:cafe::a0) by SYBPR01CA0177.outlook.office365.com
 (2603:10c6:10:52::21) with Microsoft SMTP Server (version=TLS1_2,
 cipher=TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384) id 15.20.7362.35 via Frontend
 Transport; Mon, 11 Mar 2024 00:50:04 +0000
Received-SPF: Pass (protection.outlook.com: domain of sbd.iridium.com
 designates 12.47.179.11 as permitted sender) receiver=protection.outlook.com;
 client-ip=12.47.179.11; helo=istsbdmailsv03.sbd.iridium.com; pr=C
Received: from istsbdmailsv03.sbd.iridium.com (12.47.179.11) by
 SY1PEPF00005A3F.mail.protection.outlook.com (10.167.241.38) with Microsoft
 SMTP Server (version=TLS1_2, cipher=TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384) id
 15.20.7386.12 via Frontend Transport; Mon, 11 Mar 2024 00:50:02 +0000
Received: from pps.filterd (istsbdmailsv03.sbd.iridium.com [127.0.0.1])
	by istsbdmailsv03.sbd.iridium.com (8.16.1.2/8.16.1.2) with SMTP id
 42B0kT97014829
	for <bl@list.fms.wa.gov.au>; Mon, 11 Mar 2024 00:50:01 GMT
Date: Mon, 11 Mar 2024 00:50:01 GMT
Received: from sbd.iridium.com (istsbdspp01.sbd.iridium.com [10.11.1.154])
	by istsbdmailsv03.sbd.iridium.com with ESMTP id 3wrfkh4c16-1
	for <bl@list.fms.wa.gov.au>; Mon, 11 Mar 2024 00:50:01 +0000
Reply-To: <sbdservice@sbd.iridium.com>
From: sbdservice@sbd.iridium.com
To: bl@list.fms.wa.gov.au
Subject: SBD Msg From Unit: 300034013318430
MIME-Version: 1.0
Content-Type: multipart/mixed;boundary="SBD.Boundary.605592468"
Message-ID: <3wrfkh4c16-1@istsbdmailsv03.sbd.iridium.com>
X-EOPAttributedMessage: 0
X-EOPTenantAttributedMessage: 7b934664-cdcf-4e28-a3ee-1a5bcca0a1b6:0
X-MS-PublicTrafficType: Email
X-MS-TrafficTypeDiagnostic: SY1PEPF00005A3F:EE_|ME3PR01MB8244:EE_
X-MS-Office365-Filtering-Correlation-Id: 4605cbc6-34aa-4b3e-b0e8-08dc41653034
X-LD-Processed: 7b934664-cdcf-4e28-a3ee-1a5bcca0a1b6,ExtFwd
X-MS-Exchange-AtpMessageProperties: SA
X-MS-Exchange-SenderADCheck: 0
X-MS-Exchange-AntiSpam-Relay: 0
X-Microsoft-Antispam: BCL:0;
X-Microsoft-Antispam-Message-Info: 
	ZxXZoel4iGYnnDGE5s1uJJAibTenL4tG9x7cWC2BSJdQmq/Oj8l0g9+MpbN8wneqQLuOovWyMkDL7N4i8uBZiaXPL/G6fP9KqP5T/rZ1OOcHbCquFBDt222yd08/P2E3D7Jcz+WINTCSphYBN4SauXBlM/iMdAMErZ9ntctMK5s8a+wDLzQP2TWbWAH7/EilurUwZm0PHiHKcp/jhHm8ZWZh/Edo4hxKxauwW2bL88FZOSBnF3MElHp7NnGpWyqncUyvDZ+STKZOMTNezoynH6bl6rKuRRcdOG5GvzbDFx/5DqII0WhbTBTDqbBBnzGaGdWpHIO6wfF10lqV/42kKzTyDVgymTd8dSfkKWeqJxRw1rQ0ocuK0M88vbK4zrHHIEX4yamUHQ7HZw44vqcI3wMVGfaDZ2Wc0TvlTpqjKdcesjoV6SQGgRbHIsoRzZrnt4ryKMvDkwyKETEXc13Bmj66zsGFxPjX2X4GasNsfuL3DSlGyY1D8+od0/mWMGspg8PNyoDSwTsrrPffjVT5acLRe1AjTf9k3D3P/aLwCpcqMl6rbrM/Yo6h4KwUB6FMEeNXtUY1YLFeNs9zAL1MCDAOUr5/DdKz9ca22YW7J2zZ2j03TvVWkv+hFYQLOD353WkmziqKYnbFzjJz/zk0xmJx2BRedBc5MusoE1/7fiLzCr4P4aIqEFZWxpdhhtYxv0IRbAtaI0wGZ/c2UJLoTi+WWNvFCID6icDbz2ailfQrCBqLmvWnC+IggiLiTdWp
X-Forefront-Antispam-Report: 
	CIP:12.47.179.11;CTRY:US;LANG:en;SCL:1;SRV:;IPV:NLI;SFV:NSPM;H:istsbdmailsv03.sbd.iridium.com;PTR:outbound.sbd.iridium.com;CAT:NONE;SFS:(13230031)(376005)(61400799018);DIR:OUT;SFP:1102;
X-ExternalRecipientOutboundConnectors: 7b934664-cdcf-4e28-a3ee-1a5bcca0a1b6
X-MS-Exchange-ForwardingLoop: 
	bl@list.fms.wa.gov.au;7b934664-cdcf-4e28-a3ee-1a5bcca0a1b6
X-OriginatorOrg: dbca.wa.gov.au
X-MS-Exchange-CrossTenant-OriginalArrivalTime: 11 Mar 2024 00:50:02.9310
 (UTC)
X-MS-Exchange-CrossTenant-Network-Message-Id: 
 4605cbc6-34aa-4b3e-b0e8-08dc41653034
X-MS-Exchange-CrossTenant-Id: 7b934664-cdcf-4e28-a3ee-1a5bcca0a1b6
X-MS-Exchange-CrossTenant-AuthSource: 
 SY1PEPF00005A3F.ausprd01.prod.outlook.com
X-MS-Exchange-CrossTenant-AuthAs: Anonymous
X-MS-Exchange-CrossTenant-FromEntityHeader: Internet
X-MS-Exchange-Transport-CrossTenantHeadersStamped: ME3PR01MB8244
X-Rspam-User: 
X-Rspamd-Server: rspam06
X-Rspamd-Queue-Id: AA277C0006
X-Stat-Signature: 5hu91bz4yng5tjsziyzegzhif89troer
X-Spam-Status: No, score=-4.05
X-HE-Tag: 1710118208-287611
X-HE-Meta: 
 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

SBM Message
--SBD.Boundary.605592468
Content-Type: text/plain;charset=US-ASCII
Content-Disposition: inline
Content-Transfer-Encoding: 7bit

MOMSN: 50758
MTMSN: 0
Time of Session (UTC): Mon Mar 11 00:50:00 2024
Session Status: 00 - Transfer OK
Message Size (bytes): 20

Unit Location: Lat = -34.59837 Long = 116.15538
CEPradius = 6



--SBD.Boundary.605592468
Content-Type: application/x-zip-compressed; name="SBMmessage.sbd"
Content-Disposition: attachment; filename="300034013318430_050758.sbd"
Content-Transfer-Encoding: base64

A61DU0IAYWGAESxV7mVdG5cASgE=

--SBD.Boundary.605592468--
