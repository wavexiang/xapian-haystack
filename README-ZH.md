Django的全文检索
===

我们曾经愉快的使用Haystack+Whoosh作为全文检索引擎，可伴随着数据的增加，我们毫无意外的遇到了性能问题。检索时间从毫秒级一下子跌入秒级，常常一个检所需要数秒钟才能返回。而且一旦我们要对索引内容进行调整，而不得不全部重建索引，只能等待数个小时才能建好。

为了解决这个问题，我们考察了众多的方案，并最终决定使用xapain替换Whoosh。

考察过的方案/产品包括：

* ElasticSearch 非常流行的全文搜索引擎方案。结合Kibbna、Logstash，不但可以实现我们想要的高性能全文检索功能，还能集中采集化日志处理，数据挖掘、分析等。这些也是我们非常想要的功能。放弃原因是，我们的团队规模尚小，且技术领域主要集中于Python和前端。引入ElasticSearch需要很多Java(运维)相关的技能，虽说不是完全陌生，对我们来说也是引入了较高的复杂度。
* SphinxSearch 看了很多资料。据说性能不错，但是内存占用极大。可靠性不是特别高。
* Xapain 性能出众，索引数据库小。不支持中文分词，可集成Jieba等第三方分词库。不支持多进程同时写入。

为此我们在xapain-haystack基础上，做了一些改进。增加中文分词，以及串行写入问题。

https://github.com/yuanxu/xapian-haystack


安装和配置
====
xapian-haystack提供了一个脚本，可以快速安装xapain以及Python-bindings。不过此脚本要求必须使用virtualenv环境。如果未使用请自行修改脚本。
```
source <path>/bin/activate
./install_xapian.sh 1.4.5
```

在settings.py中增加如下内容。
```
HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'extension.backends.haystack.xapian_backend.XapianEngine',
        'PATH': os.path.join(BASE_DIR, 'xapian_index'),
    },
}
HAYSTACK_SIGNAL_PROCESSOR = 'extension.backends.haystack.queued_signal.QueuedSignalProcessor'
```

添加中文支持
====
我们在Xapain-Haystack基础上，为其增加了中文支持，并改进数值型多关键字检索。


实时更新缓存
====

Xapain支持一写多读，不支持多个进程同时写入。只能使用Haystack提供的 manage.py rebuild_index周期性的更新索引库，这就造成数据的不一致性。
而我们有一个场景是将全文检索库，作为数据搜索的来源。有一定的时效性要求。
为此，我们借助redis的锁机制，以及Celery实现了串行化索引处理功能。


