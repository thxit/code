import twint
# 配置抓取参数
c = twint.Config()
c.Username = "@dotyyds1234"  # 替换为你要抓取的Twitter用户名
c.Store_csv = True
c.Output = "tweets.csv"   # 输出文件名
# 执行抓取
twint.run.Search(c)
