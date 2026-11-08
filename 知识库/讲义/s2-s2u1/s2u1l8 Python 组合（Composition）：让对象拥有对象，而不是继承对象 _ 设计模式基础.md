# s2u1l8 Python 组合（Composition）：让对象拥有对象，而不是继承对象 / 设计模式基础

> 来源 `content/lessons/s2u1l8.json`

## py.oop.composition

# Python 组合（Composition）：让对象拥有对象，而不是继承对象

## 一句话直觉

当你发现“A 里面包含一个 B，并且把活交给 B 去干”比“A 是 B 的一种”更自然时，就该用**组合（Composition）**而不是继承。

---

## 1. 什么是组合？先从“有一个”讲起

面向对象编程（Object-Oriented Programming, OOP）里，类与类之间最常见的两种关系是：

- **继承（Inheritance）**：is-a，比如 `Dog` 是 `Animal`。
- **组合（Composition）**：has-a，比如 `Car` 有一个 `Engine`。

组合的意思是：**一个类的实例把另一个类的实例作为自己的属性保存起来，并通过这个属性来完成工作**。

```python
# 电脑“有一个”CPU
class CPU:
    def run(self):
        return "CPU is computing"

class Computer:
    def __init__(self):
        # 组合：把 CPU 实例作为属性
        self.cpu = CPU()

    def start(self):
        # 把工作委托给内部的 CPU
        return self.cpu.run()

c = Computer()
print(c.start())  # CPU is computing
```

关键点：`Computer` **不是** `CPU` 的子类，它只是**拥有**一个 `CPU`。

---

## 2. 组合 vs 继承：什么时候用哪一个？

继承适合“子类天生就是父类的一种”。组合适合“一个对象由若干部件拼装而成”。

```python
# 继承版本：Dog 是一种 Animal
class Animal:
    def speak(self):
        return "..."

class Dog(Animal):
    def speak(self):
        return "Woof"

# 组合版本：Robot 有一个 Speaker 部件
class Speaker:
    def sound(self):
        return "Beep"

class Robot:
    def __init__(self, speaker):
        self.speaker = speaker  # 部件可以被替换

    def speak(self):
        return self.speaker.sound()

r = Robot(Speaker())
print(r.speak())  # Beep
```

为什么组合常常更好？

- **减少耦合**：`Robot` 不需要知道 `Speaker` 的内部实现。
- **易于替换**：换一个 `Speaker` 子类，`Robot` 不用改。
- **避免继承层级爆炸**：继承深了会很难维护。

工程上常说的原则是：**优先使用组合，而不是继承（favor composition over inheritance）**。

---

## 3. 委托：组合的核心动作

组合本身只是“持有”，真正干活的方式叫**委托（Delegation）**：外部方法调用内部对象的同名或相关方法。

```python
class Logger:
    def log(self, msg):
        print(f"[LOG] {msg}")

class Service:
    def __init__(self, logger):
        self.logger = logger

    def do_work(self):
        self.logger.log("working...")  # 委托给 logger
        return "done"

s = Service(Logger())
print(s.do_work())
```

这种“外层对象把职责交给内层对象”的模式，就是组合在 Python 里最常见的用法。

---

## 4. 依赖注入：让组合更灵活

如果组合对象在 `__init__` 里“写死”，测试时不好替换。更工程化的写法是**依赖注入（Dependency Injection）**：从外部把依赖传进来。

```python
class ConsoleLogger:
    def log(self, msg):
        print(f"console: {msg}")

class NullLogger:
    def log(self, msg):
        pass  # 测试时用空实现

class Service:
    def __init__(self, logger):
        self.logger = logger

    def do_work(self):
        self.logger.log("working...")
        return "done"

# 生产环境
Service(ConsoleLogger()).do_work()
# 测试环境：静默
Service(NullLogger()).do_work()
```

这就是组合最强大的地方：**行为可以通过替换部件来改变，而不需要改类本身**。

---

## 5. 组合在真实工程中的样子

在实际项目里，组合几乎无处不在：

- `Model` 里包含 `Tokenizer`、`Optimizer`、`Loss`。
- `WebApp` 里包含 `Router`、`Database`、`Logger`。
- 测试时把真实 `Database` 换成 `FakeDatabase`。

```python
class Database:
    def save(self, data):
        return f"saved:{data}"

class FakeDatabase:
    def save(self, data):
        return f"fake-saved:{data}"

class App:
    def __init__(self, db):
        self.db = db

    def handle(self, data):
        return self.db.save(data)

print(App(Database()).handle("a"))      # saved:a
print(App(FakeDatabase()).handle("a"))  # fake-saved:a
```

你会发现：组合让代码更**可测、可替换、可扩展**。

---

## 结尾：动手练习

**任务**：写一个 `Notifier`（通知器），它通过组合持有一个“发送渠道”。

1. 定义三个类：`EmailSender`、`SmsSender`、`PrintSender`，每个类都有 `send(msg)` 方法。
2. 定义 `Notifier` 类，构造时接收一个 sender，并把它保存为属性。
3. `Notifier` 提供 `notify(msg)`，内部委托给 sender 的 `send`。
4. 分别用三种 sender 创建 `Notifier`，调用 `notify("hello")`，观察输出。
5. 额外加一个 `FakeSender`，只把消息存到列表里，用于测试。

完成标准：你能清楚地说出——为什么这里用组合，而不是让 `Notifier` 去继承某个 Sender。

```python
# 组合示例：Notifier 拥有一个 sender，并通过委托完成任务

class EmailSender:
    def send(self, msg):
        print(f"[Email] {msg}")


class SmsSender:
    def send(self, msg):
        print(f"[SMS] {msg}")


class FakeSender:
    def __init__(self):
        self.messages = []

    def send(self, msg):
        self.messages.append(msg)  # 测试用：只记录不发送


class Notifier:
    def __init__(self, sender):
        self.sender = sender  # 组合：把发送渠道作为属性

    def notify(self, msg):
        # 委托：把真正的发送工作交给 sender
        self.sender.send(msg)


# 使用不同渠道
Notifier(EmailSender()).notify("hello")
Notifier(SmsSender()).notify("hello")

# 测试场景
fake = FakeSender()
Notifier(fake).notify("test1")
Notifier(fake).notify("test2")
print(fake.messages)  # ['test1', 'test2']
```

## py.oop.design_patterns_basic

# py.oop.design_patterns_basic：设计模式基础

## 一句话直觉

**设计模式（Design Patterns）** 是前人反复踩坑后总结出来的"代码套路"——它们不是语法，而是**面对常见设计问题时可直接复用的结构化解法**。学会它们，你就从"能写出代码"进阶到"能写出可维护、可扩展、别人看得懂的代码"。

---

## 1. 为什么需要设计模式？

初学者写代码常常是"能跑就行"。但在真实项目里，代码会被反复修改、扩展、被多人阅读。你会发现以下问题反复出现：

- 想加一个新功能，要改十几个文件；
- 一个对象创建逻辑写死了，换一种实现要重写；
- 两个模块互相依赖，改一个另一个就崩；
- 同一段代码到处复制粘贴。

设计模式就是**把这些问题归纳成 23 种命名好的解决方案**（来自 GoF《设计模式》一书）。它们最初来自 C++/Java，但在 Python 里同样适用，而且因为 Python 语法灵活，很多模式可以用更简洁的方式实现。

本讲聚焦 **4 个最常用、最基础**的模式：**单例（Singleton）**、**工厂（Factory）**、**策略（Strategy）**、**观察者（Observer）**。

---

## 2. 单例模式（Singleton）：全局只有一个实例

**用途**：配置对象、数据库连接池、日志器——这些资源全局只应存在一份，避免重复创建和状态不一致。

**核心思想**：拦截对象的创建过程，让多次调用返回同一个实例。

```python
class Config:
    _instance = None  # 类变量，保存唯一实例

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            # 首次创建时才会真正生成对象
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, env="dev"):
        # 注意：__init__ 每次都会被调用，需防止重复初始化
        if hasattr(self, "_initialized"):
            return
        self.env = env
        self._initialized = True


c1 = Config("prod")
c2 = Config("test")
print(c1 is c2)   # True
print(c2.env)     # prod（第二次的 env 参数被忽略）
```

**关键点**：`__new__` 控制实例创建；`__init__` 每次都会执行，所以要把初始化状态保护起来。

---

## 3. 工厂模式（Factory）：把"创建对象"这件事交给别人做

**用途**：当你有一组相关的类，客户端只关心"我要一个什么类型的东西"，而不想关心它到底怎么被 new 出来的。

**核心思想**：用函数或类封装创建逻辑，客户端通过参数选择类型。

```python
class Dog:
    def speak(self):
        return "Woof"

class Cat:
    def speak(self):
        return "Meow"

class Bird:
    def speak(self):
        return "Tweet"


# 简单工厂：一个函数根据参数返回不同对象
def animal_factory(kind: str):
    registry = {"dog": Dog, "cat": Cat, "bird": Bird}
    if kind not in registry:
        raise ValueError(f"Unknown animal: {kind}")
    return registry[kind]()  # 统一入口，客户端不用 new


for k in ["dog", "cat", "bird"]:
    a = animal_factory(k)
    print(k, "->", a.speak())
```

**好处**：新增 `Fish` 时，只需在 `registry` 里加一行，**客户端代码零改动**——这就是"对扩展开放，对修改关闭"（开闭原则，Open-Closed Principle）。

---

## 4. 策略模式（Strategy）：把"算法"变成可替换的对象

**用途**：同一件事有多种做法（如排序、打折、压缩算法），希望运行时能切换而不改调用方。

**核心思想**：把每种算法封装成一个类，用统一的接口调用。

```python
from abc import ABC, abstractmethod

class DiscountStrategy(ABC):
    @abstractmethod
    def apply(self, price: float) -> float: ...

class NoDiscount(DiscountStrategy):
    def apply(self, price): return price

class TenPercentOff(DiscountStrategy):
    def apply(self, price): return price * 0.9

class HalfOff(DiscountStrategy):
    def apply(self, price): return price * 0.5


class Order:
    def __init__(self, price: float, strategy: DiscountStrategy):
        self.price = price
        self.strategy = strategy  # 依赖抽象，不依赖具体实现

    def total(self) -> float:
        return self.strategy.apply(self.price)


print(Order(100, NoDiscount()).total())    # 100
print(Order(100, TenPercentOff()).total()) # 90.0
print(Order(100, HalfOff()).total())       # 50.0
```

**要点**：`Order` 只认识抽象基类 `DiscountStrategy`，新增折扣方式时不需要改 `Order`。

---

## 5. 观察者模式（Observer）：一对多的事件通知

**用途**：当一个对象（被观察者）状态变化时，自动通知所有关心它的人（观察者）。常见于 UI 事件、消息订阅、MVC 中的模型-视图同步。

**核心思想**：观察者注册到主题上，主题变化时逐个回调。

```python
class Subject:
    def __init__(self):
        self._observers = []

    def subscribe(self, observer):
        self._observers.append(observer)

    def notify(self, event):
        for obs in self._observers:
            obs.update(event)


class EmailNotifier:
    def update(self, event):
        print(f"[Email] 收到事件: {event}")

class SMSNotifier:
    def update(self, event):
        print(f"[SMS] 收到事件: {event}")


subject = Subject()
subject.subscribe(EmailNotifier())
subject.subscribe(SMSNotifier())
subject.notify("订单已发货")
```

**输出**：
```
[Email] 收到事件: 订单已发货
[SMS] 收到事件: 订单已发货
```

**好处**：新增一种通知方式（如微信推送）只需再加一个观察者，**主题代码完全不动**。

---

## 6. 什么时候"不该"用设计模式？

设计模式是**工具，不是 KPI**。以下情况应避免：

- 只有一个实现、短期不会变：不需要工厂 / 策略，直接写就好。
- 需求还完全不清楚：先写能跑的原型。模式是用来**应对变化的**，没变化就不用。
- 追求"看起来高级"：过度抽象会让代码更难读。

**原则**：先写简单代码，当发现重构痛点反复出现时，再引入相应的模式。

```python
"""
综合示例：一个简化的订单系统，同时演示 4 个基础设计模式。
直接 python 运行即可。
"""
from abc import ABC, abstractmethod

# ---------- 1. 单例：全局配置 ----------
class AppConfig:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.tax_rate = 0.1  # 全局税率
        return cls._instance


# ---------- 2. 策略：折扣算法 ----------
class Discount(ABC):
    @abstractmethod
    def apply(self, price: float) -> float: ...

class NoDiscount(Discount):
    def apply(self, price): return price

class TenPercentOff(Discount):
    def apply(self, price): return price * 0.9


# ---------- 3. 工厂：根据名字造折扣 ----------
class DiscountFactory:
    _registry = {
        "none": NoDiscount,
        "ten_off": TenPercentOff,
    }

    @classmethod
    def create(cls, name: str) -> Discount:
        if name not in cls._registry:
            raise ValueError(f"未知折扣类型: {name}")
        return cls._registry[name]()


# ---------- 4. 观察者：订单状态变化通知 ----------
class OrderSubject:
    def __init__(self):
        self._observers = []

    def subscribe(self, observer):
        self._observers.append(observer)

    def notify(self, event: str):
        for obs in self._observers:
            obs.update(event)


class Logger:
    def update(self, event):
        print(f"[LOG] {event}")


class EmailService:
    def update(self, event):
        print(f"[EMAIL] 用户收到: {event}")


# ---------- 组装：下订单流程 ----------
class Order:
    def __init__(self, price: float, discount_name: str):
        self.price = price
        self.discount = DiscountFactory.create(discount_name)
        self.subject = OrderSubject()

    def subscribe(self, observer):
        self.subject.subscribe(observer)

    def total(self) -> float:
        discounted = self.discount.apply(self.price)
        return round(discounted * (1 + AppConfig().tax_rate), 2)

    def checkout(self):
        self.subject.notify(f"订单已结算，总价 {self.total()} 元")


if __name__ == "__main__":
    order = Order(price=200, discount_name="ten_off")
    order.subscribe(Logger())
    order.subscribe(EmailService())
    order.checkout()
```


---

## 本课题目

### single_choice · None



- [A] 让 Car 类继承 Engine 类，从而获得发动机的所有属性和方法。
- [B] 在 Car 类的 __init__ 方法中创建一个 Engine 实例并赋值给 self.engine。
- [C] 在 Car 类中定义一个方法，该方法内部临时创建一个 Engine 实例并使用后丢弃。
- [D] 在 Car 类中通过类变量 engine = Engine() 让所有汽车实例共享同一个发动机。

**参考答案**：1

**解析**：组合的核心是“拥有一个”（has-a）关系：一个对象把另一个对象作为自己的属性持有，并在需要时使用它。选项 B 正确地在实例初始化时把 Engine 实例保存为属性，体现了组合。选项 A 是继承（is-a），不符合“包含”的语义；选项 C 只是临时使用，没有形成稳定的整体-部分关系；选项 D 虽然持有 Engine，但用类变量会让所有实例共享同一个发动机，通常不是期望的每个汽车拥有自己的发动机。

### single_choice · None



- [A] Car 继承自 Engine，因此可以直接调用 start 方法。
- [B] Car 和 Engine 之间是组合关系，Car 通过持有的 Engine 实例来完成任务。
- [C] 这段代码无法运行，因为 self.engine 不是 Car 的属性。
- [D] Engine 实例是 Car 的类变量，所有 Car 实例共享同一个 Engine。

**参考答案**：1

**解析**：在 Car 的 __init__ 中，self.engine = Engine() 把 Engine 实例保存为 Car 实例的属性，属于组合关系；Car.drive 通过 self.engine.start() 委托给持有的 Engine 对象。Car 并没有继承 Engine，所以选项 A 错误；self.engine 是实例属性，选项 C 错误；它是实例属性而不是类变量，选项 D 错误。

### single_choice · None



- [A] 整体对象应该直接复制部分对象的所有代码，以避免依赖。
- [B] 整体对象通常负责协调部分对象，而不是把所有部分的功能都实现在自己内部。
- [C] 部分对象不应该有自己的方法，否则会破坏组合。
- [D] 整体对象必须继承部分对象，才能协调部分对象的行为。

**参考答案**：1

**解析**：在组合中，整体通过持有部分对象并调用它们的方法来完成任务，职责通常划分清晰：部分实现自己的功能，整体负责协调。选项 A 的“复制代码”会失去组合的意义；选项 C 错误，部分对象通常有自己的方法；选项 D 错误，组合不要求继承。

### single_choice · None



- [A] class A(B): pass
- [B] class A:
      def __init__(self):
          self.b = B()
- [C] class A:
      b = B
- [D] class A:
      def b(self):
          return B

**参考答案**：1

**解析**：选项 B 在 A 的 __init__ 中创建 B 实例并保存为 self.b，这是组合的典型写法。选项 A 是继承；选项 C 把类对象 B 赋给类变量 b，持有的是类而不是实例，并且是类级别共享，通常不视为期望的实例组合；选项 D 定义了一个返回类 B 的方法，也没有持有 B 的实例。

### single_choice · None



- [A] Office 继承自 Printer，因此可以调用 print_doc。
- [B] Office 通过组合持有一个 Printer 实例，可以在需要时调用 self.printer.print_doc。
- [C] 这段代码有语法错误，因为 Printer 没有在 Office 之前定义。
- [D] Printer 实例是 Office 的类变量，所有 Office 实例共享同一个打印机。

**参考答案**：1

**解析**：Office 的 __init__ 中 self.printer = Printer() 表明 Office 持有一个 Printer 实例，是组合关系，之后可以通过 self.printer 调用 Printer 的方法。Office 没有继承 Printer，选项 A 错误；只要 Printer 在创建实例时已定义即可，选项 C 错误；self.printer 是实例属性，不是类变量，选项 D 错误。

### single_choice · None



- [A] 组合关系中，整体对象可以无条件替换部分对象为任意其他对象，不需要考虑接口。
- [B] 组合关系中，只要部分对象提供整体所需的方法，整体就可以使用它，这提高了灵活性。
- [C] 组合关系中，部分对象必须是整体对象的子类。
- [D] 组合关系中，整体对象不能替换部分对象，因为部分对象是写死的。

**参考答案**：1

**解析**：组合的灵活性在于：整体只依赖部分对象所提供的接口，只要传入的对象有需要的方法，就可以替换，便于扩展和测试。选项 A 错误，替换仍需满足接口；选项 C 错误，部分对象不要求是整体的子类；选项 D 错误，部分对象通常可以通过参数等方式替换。

### single_choice · None



- [A] 让 Order 继承自具体的支付类，例如 WeChatPay，这样 Order 就具有支付能力。
- [B] 在 Order 中定义一个 pay 方法，方法内部写死使用某一种支付方式。
- [C] 定义一个支付接口或支付类，然后让 Order 持有一个支付对象，在创建 Order 时注入具体支付方式。
- [D] 为每种支付方式创建一个 Order 子类，例如 WeChatOrder、AliPayOrder。

**参考答案**：2

**解析**：组合允许 Order 持有一个支付对象，并通过该对象完成支付；在创建 Order 时注入不同的支付实现，可以方便地扩展新的支付方式，同时避免 Order 与具体支付方式之间的强耦合。选项 A 让 Order 继承具体支付类，语义不当且不易扩展；选项 B 写死支付方式，违反开闭原则；选项 D 通过继承为每种支付方式创建 Order 子类，会导致类爆炸，也不如组合灵活。

### single_choice · None



- [A] 'processing'
- [B] 'CPU'
- [C] 'Computer'
- [D] 报错，因为 Computer 没有 process 方法。

**参考答案**：0

**解析**：Computer 通过组合持有一个 CPU 实例。调用 c.run() 时，run 内部调用 self.cpu.process()，而 CPU.process 返回字符串 'processing'，因此输出 'processing'。选项 B、C 是类名，不是返回值；选项 D 错误，因为 run 是通过 self.cpu 调用 process，并不要求 Computer 自己有 process 方法。

### single_choice · None



- [A] 整体对象把部分对象的属性复制一份，自己直接使用。
- [B] 整体对象把某个任务交给持有的部分对象去完成，通过调用部分对象的方法来实现。
- [C] 整体对象继承部分对象，从而获得部分对象的方法。
- [D] 部分对象继承整体对象，从而获得整体对象的方法。

**参考答案**：1

**解析**：委托是组合中常见的协作方式：整体持有部分对象，当需要完成某个功能时，把任务交给部分对象处理，即调用部分对象的相应方法。选项 A 描述的是复制而不是委托；选项 C、D 描述的是继承关系，不是组合中的委托。

### single_choice · None



- [A] class Team:
      players = []
- [B] class Team:
      def __init__(self):
          self.players = []
- [C] class Team(Player):
      pass
- [D] class Team:
      def players(self):
          return Player

**参考答案**：1

**解析**：选项 B 在 __init__ 中为每个 Team 实例创建独立的 players 列表，用于存放 Player 对象，体现组合，并且各实例互不影响。选项 A 使用类变量 players，所有 Team 实例共享同一个列表，通常不是期望的；选项 C 是继承；选项 D 定义了一个返回 Player 类的方法，并没有持有 Player 实例的集合。

### single_choice · None



- [A] 组合可以降低类之间的耦合，因为整体只依赖部分提供的接口。
- [B] 组合可以在运行时替换部分对象，从而提高灵活性。
- [C] 组合可以避免继承层次过深带来的复杂性。
- [D] 组合要求整体必须继承部分，因此比继承更耦合。

**参考答案**：3

**解析**：组合不要求整体继承部分，整体只是持有部分对象并通过接口使用它，因此通常比继承的耦合更弱，而不是更强。选项 A、B、C 都是组合的常见优点：降低耦合、运行时替换、避免继承层次过深。选项 D 的说法与组合的基本思想相反。

### single_choice · None



- [A] 不能替换，因为 Robot 在 __init__ 中写死了 Speaker。
- [B] 可以替换，只要传入的对象具有 speak 方法，Robot.greet 就能工作。
- [C] 只能通过继承 Speaker 来替换。
- [D] 替换后必须修改 Robot 类的源码，否则无法运行。

**参考答案**：1

**解析**：Robot 通过组合持有一个 speaker 对象，并在 greet 中调用 self.speaker.speak('hello')。只要传入的对象有 speak 方法，就可以正常工作，这体现了组合带来的灵活性和松耦合。选项 A、C、D 都错误，因为 Robot 并没有写死 Speaker 类，也不要求替换对象继承 Speaker，通常也不需要修改 Robot 源码。

### single_choice · None



- [A] 组合表达“是一个”（is-a）关系，继承表达“有一个”（has-a）关系。
- [B] 组合表达“有一个”（has-a）关系，继承表达“是一个”（is-a）关系。
- [C] 组合只能在 __init__ 中使用，继承只能在类定义时使用。
- [D] 组合不能复用代码，继承才能复用代码。

**参考答案**：1

**解析**：组合通常表达“有一个”关系：一个对象持有另一个对象作为组成部分；继承表达“是一个”关系：子类是父类的一种特化。选项 A 把两者说反了；选项 C 错误，组合不限于 __init__，也可以在运行时替换组件；选项 D 错误，组合同样可以实现代码复用，只是方式不同。

### single_choice · None



- [A] 需要表达“学生是人”这样的关系。
- [B] 需要表达“汽车有发动机”这样的关系。
- [C] 需要让子类自动获得父类的所有属性和方法。
- [D] 需要重写父类的某个方法以改变行为。

**参考答案**：1

**解析**：“汽车有发动机”是“有一个”关系，适合组合。选项 A 是“是一个”关系，适合继承；选项 C 描述的是继承带来的效果；选项 D 是继承中方法重写的场景，与选择组合的理由不同。

### single_choice · None



- [A] 让 Order 继承自 Product，使订单自动拥有商品的所有属性。
- [B] 在 Order 的 __init__ 中接收一个商品列表，并保存为 self.products。
- [C] 在 Order 中定义一个全局变量 products，所有订单共享同一份商品列表。
- [D] 在 Order 中定义方法 add_product，每次调用时临时打印商品信息后丢弃商品对象。

**参考答案**：1

**解析**：组合允许一个对象包含多个其他对象作为组成部分。订单包含多个商品，适合在 Order 中维护一个商品集合（如 self.products），这是组合的典型应用。选项 A 是继承，语义错误（订单不是商品）；选项 C 使用全局变量会导致所有订单共享数据，通常不是期望设计；选项 D 没有真正把商品作为订单的组成部分持有。

### single_choice · None



- [A] 组合关系中，部分对象的生命周期总是独立于整体对象，整体销毁后部分仍然存在。
- [B] 在典型的组合关系中，部分对象通常由整体对象创建和持有，整体对象销毁时部分对象也不再被使用。
- [C] 组合关系中，部分对象必须是全局变量，否则无法被整体对象使用。
- [D] 组合关系中，整体对象必须继承部分对象，才能管理其生命周期。

**参考答案**：1

**解析**：组合通常表示强“拥有”关系：整体负责创建并持有部分，整体不存在时，部分通常也随之失去意义。选项 A 描述的是聚合等较弱的关系；选项 C 错误，部分对象可以是实例属性而不必是全局变量；选项 D 错误，组合不要求继承，继承反而会改变关系语义。

### single_choice · None



- [A] UserService 继承了 Logger，因此可以直接调用 print。
- [B] UserService 通过组合持有一个 Logger，可以在创建时注入不同的日志实现，降低耦合。
- [C] UserService 无法替换 Logger，因为 logger 被写死了。
- [D] Logger 成为 UserService 的类变量，所有 UserService 实例共享同一个日志对象。

**参考答案**：1

**解析**：这里 UserService 通过 __init__ 接收一个 logger 对象并保存为实例属性，体现了组合和依赖注入的思想：可以在创建 UserService 时传入不同的 Logger 实现，便于替换和测试。选项 A 错误，UserService 没有继承 Logger；选项 C 错误，logger 是通过参数传入的，可以替换；选项 D 错误，self.logger 是实例属性而不是类变量。

### single_choice · None



- [A] 子类与父类之间是明确的“是一种”关系，例如狗是一种动物。
- [B] 一个类需要复用另一个类的实现，但两者之间并不是“是一种”关系，例如汽车需要一个发动机。
- [C] 子类需要重写父类的所有方法。
- [D] 父类中的方法都是抽象方法，子类必须实现。

**参考答案**：1

**解析**：当两个类之间是“有一个”关系而不是“是一种”关系时，组合通常比继承更合适。汽车“有一个”发动机，而不是“是一种”发动机，所以适合组合。选项 A 是继承的典型场景；选项 C 和 D 描述的是继承中的方法重写和抽象方法，与选择组合还是继承的理由无关。

### single_choice · None



- [A] Bicycle 通过组合持有了两个 Wheel 实例。
- [B] Bicycle 和 Wheel 之间是“有一个”关系。
- [C] Bicycle 继承自 Wheel，因此可以调用 rotate 方法。
- [D] 如果 Wheel 的 rotate 方法改变，Bicycle.move 的行为可能受到影响。

**参考答案**：2

**解析**：Bicycle 在 __init__ 中创建了两个 Wheel 实例并保存为属性，属于组合关系（“有一个”），所以选项 A、B 正确。组合中整体依赖部分的行为，部分改变可能影响整体，选项 D 正确。Bicycle 并没有继承 Wheel，选项 C 说“继承自 Wheel”是错误的。

### single_choice · None



- [A] 在 Computer 的 __init__ 中创建 CPU、内存和硬盘实例，并分别保存为属性。
- [B] 通过参数把 CPU、内存和硬盘实例传给 Computer 的 __init__，并保存为属性。
- [C] 让 Computer 继承 CPU，从而直接获得 CPU 的所有方法。
- [D] 在 Computer 中定义方法，通过这些属性调用各个部件的功能。

**参考答案**：2

**解析**：组合的核心是持有其他对象作为组成部分。选项 A、B、D 都体现了 Computer 持有 CPU、内存、硬盘等部件，并通过它们完成任务。选项 C 让 Computer 继承 CPU，表达的是“电脑是一种 CPU”，这不符合“电脑包含 CPU”的现实语义，也不符合组合思想。

### single_choice · None



- [A] 200
- [B] Engine
- [C] Car
- [D] None

**参考答案**：0

**解析**：创建 Car 时传入了 Engine(200)，该 Engine 实例被保存为 car.engine。Engine 的 __init__ 把 power 设为 200，因此 car.engine.power 是 200。选项 B、C 是类名而不是属性值；选项 D 错误，因为 power 已经被赋值为 200。

### single_choice · None



- [A] 把类中所有方法都写成 public，便于子类随意重写
- [B] 定义抽象基类声明操作，由具体子类提供不同实现
- [C] 将所有逻辑集中在一个大类中，避免继承层次
- [D] 使用全局变量保存配置，所有函数共享读取

**参考答案**：1

**解析**：抽象基类声明「做什么」，子类实现「怎么做」，从而让意图与实现解耦、可各自独立扩展。选项 A 破坏封装，C 导致上帝类，D 引入全局状态耦合，均不符合该原则。

### single_choice · None



- [A] 调用方只依赖抽象类型声明的方法，不关心具体对象是谁
- [B] 代码中不允许出现任何抽象类或基类
- [C] 只有使用接口（interface）关键字的语言才能做到
- [D] 面向实现编程意味着必须使用多重继承

**参考答案**：0

**解析**：该原则的核心是依赖抽象而非具体实现，Python 中没有 interface 关键字，使用抽象基类或鸭子类型即可实现。B、C、D 都是常见误解。

### single_choice · None



- [A] 只要代码能运行就应尽量套用尽可能多的设计模式
- [B] 先理解问题与变化点，再在确有需要时引入模式，避免过度设计
- [C] 设计模式属于理论，实践中一律不用
- [D] 使用模式后代码一定更易读，无需衡量成本

**参考答案**：1

**解析**：设计模式是应对特定变化点的经验总结，是否使用应基于问题本身。盲目套用会带来不必要的抽象和复杂度，完全排斥也会错失成熟的解决思路。

### multi_choice · None



- [A] 单例模式
- [B] 工厂方法模式
- [C] 观察者模式
- [D] 建造者模式

**参考答案**：[0, 1, 3]

**解析**：单例、工厂方法、建造者都关注对象的创建。观察者属于行为型模式，关注对象间的通信与职责分配。

### multi_choice · None



- [A] 让 Wrapper 的子类分别实现日志与缓存，可依次包裹对象实现叠加
- [B] 只要继承 Service 即可自动获得日志与缓存功能
- [C] 这种通过持有并委托内部对象的方式体现了组合优于继承的思想
- [D] Wrapper 必须修改 Service 类的源码才能生效

**参考答案**：[0, 2]

**解析**：包装类持有并委托内部对象，是装饰器/组合思路。子类分别实现不同职责后可多层包裹叠加功能；无需修改原类；单纯继承 Service 不会自动获得新功能。

### multi_choice · None



- [A] 被观察者通常提供注册和注销观察者的方法
- [B] 观察者需要提供被通知时调用的统一回调接口
- [C] 被观察者一般在状态变化后主动通知观察者，而不是等待轮询
- [D] 观察者模式要求所有观察者必须是同一具体类

**参考答案**：[0, 1, 2]

**解析**：观察者模式要求可注册/注销、有统一通知接口、由被观察者主动推送。观察者可以是不同类的对象，只要符合统一接口，因此 D 错误。

### multi_choice · None



- [A] 策略对象之间通常可以互相替换，因为它们实现了同一抽象接口
- [B] 调用方通过组合持有一个策略对象，可在运行时切换策略
- [C] 策略模式能够消除所有的条件分支，无论条件是否与算法选择有关
- [D] 引入策略模式会带来额外的类与对象，需要权衡复杂度

**参考答案**：[0, 1, 3]

**解析**：策略模式让可互换算法遵循同一接口，调用方组合持有并可运行时替换，同时会引入更多类型需权衡。它只能消除「因算法选择」产生的分支，不能消除所有条件分支，C 过于绝对。

### fill_blank · None



**参考答案**：["__new__", "new", "__new__()"]

**解析**：对象创建由 __new__ 负责，因此单例应在 __new__ 中判断缓存，若已存在就返回已有实例。__init__ 只负责初始化，无法阻止新对象被创建。

### fill_blank · None



**参考答案**：["行为", "behavioral", "行为型"]

**解析**：经典分类把设计模式分为创建型、结构型和行为型。行为型关注对象间的职责分配与通信，如观察者、策略、模板方法等。

### fill_blank · None



**参考答案**：["接口", "抽象", "抽象类型"]

**解析**：面向接口（抽象）编程意味着依赖抽象而非具体实现，从而使具体策略可替换、系统更易扩展。

### code_reading · None



**参考答案**：输出两行：A got hi 和 B got hi。体现了观察者模式思想：Subject 维护观察者列表，状态/事件触发时遍历调用各观察者的 update 方法进行通知。

**解析**：attach 把观察者加入列表，notify 遍历列表逐一调用 update，A、B 的 update 各打印一行。这正是被观察者主动推送、观察者统一回调的观察者模式。

### code_reading · None



**参考答案**：它通过重写 __new__ 并缓存 _instance 来实现单例，保证同名类在单线程下只创建一个实例。缺陷是：在多线程并发首次创建时存在竞态，可能创建出多个实例，需要加锁；此外 __init__ 仍可能被重复调用，需要额外处理。

**解析**：该实现在单线程顺序调用下正确，但「检查-创建」不是原子操作，多线程下可能都通过 is None 判断，从而产生多个实例。常见改进是用锁保护创建过程，并考虑 __init__ 的重复执行问题。

### single_choice · None



- [A] 策略模式只能处理数值计算，工厂只能创建对象
- [B] 策略模式把可替换的算法封装成独立对象，让算法可互换；工厂关注的是对象创建
- [C] 策略模式必须用继承，工厂必须用组合
- [D] 两者完全等价，只是命名不同

**参考答案**：1

**解析**：策略模式封装的是「可互换的算法/行为」，工厂模式封装的是「对象的创建过程」，二者的关注点不同。其余选项混淆了职责。

### scenario · None



**解析**：该场景的根因是「算法随类型变化」，属于策略模式的典型适用点。应把每种用户类型的折扣运费算法封装为独立策略类，遵循同一抽象接口，结账方法组合持有策略并在运行时选择；新增用户类型只需新增策略实现，无需修改结账代码，从而降低修改风险、符合开闭原则。

### single_choice · None



- [A] 它能保证一个类在进程内只有一个实例，并提供全局访问点
- [B] 它保证实例的线程安全，无需任何额外处理
- [C] 它提升了代码可测试性，因为全局状态更易替换
- [D] 它是实现继承复用的最佳方式

**参考答案**：0

**解析**：单例的核心目标就是「进程内唯一实例 + 全局访问点」。它本身不自动保证线程安全，且全局状态通常会降低可测试性，也与继承复用无关，因此 B、C、D 错误。

### single_choice · None



- [A] 一份所有观察者的引用列表，并在状态变化时逐个通知
- [B] 一份所有观察者的类定义副本
- [C] 一个全局字典，记录所有观察者的实例数量
- [D] 一个独立线程，用于定期轮询观察者

**参考答案**：0

**解析**：Subject 维护观察者集合，状态变化时遍历集合调用其更新方法。轮询可由观察者自行实现，但观察者模式的核心是「发布-订阅式通知」，而非由 Subject 起线程轮询。

### single_choice · None



- [A] 装饰器模式无需修改原类即可动态叠加功能，避免继承层次爆炸
- [B] 装饰器模式一定比继承运行更快
- [C] 装饰器模式可以完全替代所有继承场景
- [D] 装饰器模式能自动实现序列化

**参考答案**：0

**解析**：装饰器通过组合在运行时叠加职责，能避免为每种功能组合创建子类导致的类爆炸。它并非性能更优，也不能完全取代继承，与序列化无关。

### single_choice · None



- [A] 适配器用于转换接口以匹配调用方期望，外观用于为一组复杂子系统提供统一简化接口
- [B] 两者的目的完全相同，都是简化接口
- [C] 外观模式会改变被包装对象的接口定义
- [D] 适配器必须与子系统一一对应

**参考答案**：0

**解析**：适配器侧重「接口转换」，外观侧重「统一简化入口」。两者目的不同；外观通常不改变原接口；适配器可一次对应多个类，故 B、C、D 错误。

### single_choice · None



- [A] 定义创建对象的接口，由子类决定实例化哪个类，把实例化延迟到子类
- [B] 把产品的所有构造函数合并成一个全局函数
- [C] 强制所有产品必须继承同一个具体类
- [D] 在编译期确定对象类型，禁止动态创建

**参考答案**：0

**解析**：工厂方法把「创建哪种产品」的决定权交给子类，实现创建与使用解耦。其余选项都是对工厂方法的误解。

### single_choice · None



- [A] 策略模式
- [B] 单例模式
- [C] 建造者模式
- [D] 原型模式

**参考答案**：0

**解析**：checkout 依赖抽象 Payment，具体支付算法由传入的子类对象提供，是可互换的算法封装，属于策略模式思想。

### single_choice · None



- [A] 重写 __new__，若已有实例则返回它，否则创建并缓存
- [B] 重写 __init__，让它在第二次调用时抛出异常
- [C] 使用 __del__ 阻止对象被销毁
- [D] 使用 __slots__ 限制属性数量

**参考答案**：0

**解析**：控制实例数量的关键是拦截对象创建环节，即重写 __new__ 并缓存首次实例。仅重写 __init__ 无法阻止 __new__ 创建新对象，__del__ 与 __slots__ 与该目标无关。
