// SPDX-License-Identifier: MIT
#include <QObject>
#include <QQmlExtensionPlugin>
#include <qqml.h>
#include <dlfcn.h>

// SceneEffect drops key events before its asynchronous view exists. Observe
// KWin's modifier signal instead: it is emitted before input filters run.
// Only QObject reflection is used; this does not link KWin's private C++ API.
class InputState : public QObject
{
    Q_OBJECT
    Q_PROPERTY(int modifiers READ modifiers NOTIFY modifiersChanged)
    Q_PROPERTY(bool available READ available CONSTANT)
public:
    explicit InputState(QObject *parent = nullptr) : QObject(parent)
    {
        void *symbol = dlsym(RTLD_DEFAULT, "_ZN4KWin16InputRedirection6s_selfE");
        if (!symbol) return;
        auto input = *static_cast<QObject **>(symbol);
        if (!input || QByteArray(input->metaObject()->className()) != "KWin::InputRedirection") return;
        m_available = bool(connect(input,
            SIGNAL(keyboardModifiersChanged(Qt::KeyboardModifiers,Qt::KeyboardModifiers)),
            this, SLOT(updateModifiers(Qt::KeyboardModifiers,Qt::KeyboardModifiers))));
    }
    int modifiers() const { return m_modifiers; }
    bool available() const { return m_available; }
public slots:
    void updateModifiers(Qt::KeyboardModifiers current, Qt::KeyboardModifiers)
    {
        if (m_modifiers == int(current)) return;
        m_modifiers = int(current);
        emit modifiersChanged();
    }
signals:
    void modifiersChanged();
private:
    int m_modifiers = 0;
    bool m_available = false;
};

class InputStatePlugin : public QQmlExtensionPlugin
{
    Q_OBJECT
    Q_PLUGIN_METADATA(IID QQmlExtensionInterface_iid)
public:
    void registerTypes(const char *uri) override
    {
        qmlRegisterSingletonType<InputState>(uri, 1, 0, "InputState",
            [](QQmlEngine *, QJSEngine *) -> QObject * { return new InputState; });
    }
};

#include "inputstate.moc"
