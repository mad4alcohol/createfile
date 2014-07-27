# encoding: utf-8
import logging
import time
import os
import webbrowser
from PySide.QtGui import *
from PySide.QtCore import *
from PySide.QtWebKit import QWebView
from jinja2 import Environment, PackageLoader
from ..widgets import FilesWidget, SummaryWidget, FigureWidget, RulesWidget, \
    FAT32SettingsWidget, NTFSSettingsWidget
from ..misc import AsyncTaskMixin, info_box
from drive.fs.fat32 import FAT32
import matplotlib.pyplot as plt

class BaseSubWindow(QMainWindow, AsyncTaskMixin):

    signal_partition_parsed = Signal(object)

    USE_QT_WEBKIT = False
    MEASURE_RELOAD_TIME = True

    def __init__(self,
                 parent,
                 partition, partition_address):
        super().__init__(parent=parent)

        self.setup_mixin(parent)

        self.partition = partition
        self.partition_address = partition_address

        self.summary_widget = SummaryWidget(self, self.partition.type)
        self.files_widget = FilesWidget(self)
        self.rules_widget = RulesWidget(self)

        self.figures_widget = QTabWidget(self)
        self.figures_widget.setTabsClosable(True)

        def close_tab(id_):
            w = self.figures_widget.widget(id_)
            plt.close(w.figure)

            self.figures_widget.removeTab(id_)
        self.figures_widget.tabCloseRequested.connect(close_tab)

        if self.partition.type == FAT32.type:
            self.settings = self.settings_widget = FAT32SettingsWidget(self)
        else:
            self.settings = self.settings_widget = NTFSSettingsWidget(self)

        self.setup_layout()

        self.setWindowIcon(QFileIconProvider().icon(QFileIconProvider.Drive))
        self.setAttribute(Qt.WA_DeleteOnClose)

        self.template_path = os.path.join(os.getcwd(),
                                          'gui',
                                          'sub_windows', 'templates')
        self.timeline_base_url = QUrl.fromLocalFile(self.template_path)

        jinja_env = Environment(loader=PackageLoader('gui.sub_windows'))
        self.timeline_template = jinja_env.get_template('timeline.html')

        self.original_title = '正在分析%s' % partition_address
        self.setWindowTitle(self.original_title)

        self.logger = logging.getLogger(__name__)

        self.raw_entries = None
        self.entries = None

        self.abnormal_files = set()

        self.reload()

    def reload(self):
        reload_start_time = time.time()

        self.raw_entries = None
        self.entries = None

        self.abnormal_files = set()

        def _slot(entries):
            self.entries = entries

            target_finished_time = time.time()

            _1 = time.time()
            print('filtering and sorting entries...')
            self.entries = self.settings.filter(self.entries)
            self.entries = self.settings.sort(self.entries)
            _1f = time.time()

            self.entries = self.apply_rules(self.entries)

            _2 = time.time()
            print('generating summary...')
            self.summary_widget.summarize(self.entries)
            self.summary_widget.set_summary()
            _2f = time.time()

            _3 = time.time()
            print('deducing abnormal files...')
            self.entries = self.deduce_abnormal_files(self.entries)
            _3f = time.time()

            _4 = time.time()
            print('deducing authentic time...')
            self.entries = self.deduce_authentic_time(self.entries)
            _4f = time.time()

            _5 = time.time()
            print('displaying files in files widget...')
            self.show_files(self.entries)
            _5f = time.time()

            self.signal_partition_parsed.disconnect(_slot)

            print('reload finished')
            reload_finish_time = time.time()

            if self.MEASURE_RELOAD_TIME:
                print('reloading elapsed: %s,\n'
                      'target elapsed:    %s,\n'
                      '_1 elapsed:        %s,\n'
                      '_2 elapsed:        %s,\n'
                      '_3 elapsed:        %s,\n'
                      '_4 elapsed:        %s,\n'
                      '_5 elapsed:        %s,\n' % (
                    reload_finish_time - reload_start_time,
                    target_finished_time - target_start_time,
                    _1f - _1, _2f - _2, _3f - _3, _4f - _4, _5f - _5
                ))

        def _target():
            return self.normalize_entries(self.partition.get_entries())

        self.signal_partition_parsed.connect(_slot)

        target_start_time = time.time()
        self.do_async_task(_target,
                           signal_after=self.signal_partition_parsed,
                           title_before='正在读取分区...')

    def deduce_abnormal_files(self, entries):
        raise NotImplementedError

    def setup_related_buttons(self):
        raise NotImplementedError

    def setup_layout(self):
        buttons_layout = self.setup_related_buttons()

        def new_group_box(widget, title):
            _ = QVBoxLayout()
            _.addWidget(widget)

            group_box = QGroupBox(title)
            group_box.setLayout(_)

            return group_box

        summary_group_box = new_group_box(self.summary_widget, '分区概要')
        files_group_box = new_group_box(self.files_widget, '分区文件列表')
        settings_group_box = new_group_box(self.settings_widget, '设置')
        rules_group_box = new_group_box(self.rules_widget, '规则列表')

        _1 = QVBoxLayout(self)
        _1.addLayout(buttons_layout)
        _1.addWidget(summary_group_box)
        _1.addWidget(settings_group_box)

        _2 = QVBoxLayout(self)
        _2.addWidget(files_group_box)
        _2.addWidget(rules_group_box)

        __1 = QHBoxLayout()
        __1.addLayout(_1)
        __1.addLayout(_2)
        _w = QWidget()
        _w.setLayout(__1)

        _3 = QVBoxLayout(self)
        _3.addWidget(self.figures_widget)
        _3w = QWidget()
        _3w.setLayout(_3)

        splitter = QSplitter()
        splitter.addWidget(_w)
        splitter.addWidget(_3w)

        self.setCentralWidget(splitter)

    def show_files(self, entries):
        self.files_widget.clear()

        for _, row in entries.iterrows():
            self.files_widget.append(self.gen_file_row_data(row))

    def gen_file_row_data(self, row):
        raise NotImplementedError

    def apply_rules(self, entries):
        return self._apply_rules(entries,
                                 self.rules_widget.rules())

    @staticmethod
    def normalize_entries(entries):
        entries['abnormal'] = False
        entries['abnormal_src'] = [[] for _ in range(entries.shape[0])]
        entries['conclusions'] = [[] for _ in range(entries.shape[0])]
        entries['deduced_time'] = ''

        return entries

    @staticmethod
    def _apply_rules(entries, rules):
        for r_id, rule in enumerate(rules):
            _result, positives, e = rule.apply_to(entries)

            for i, (r, (_, o)) in enumerate(zip(_result, e.iterrows())):
                if _ not in entries.index:
                    # wtf???
                    print('warning, entries missing index %s' % _)
                    continue

                entries.loc[_, 'conclusions'].extend(r.conclusions)

                if rule.abnormal:
                    if i in positives:
                        entries.loc[_, 'abnormal'] = True
                        entries.loc[_, 'abnormal_src'].append('%s号规则' % r_id)

        return entries

    @staticmethod
    def deduce_authentic_time(e):
        entries = e.sort(columns=['first_cluster'])
        reversed_entries_list = list(reversed(list(map(lambda _: _[1],
                                                       entries.iterrows()))))

        visited_files = set()

        first_entry, last_entry = entries.iloc[0], entries.iloc[-1]

        for _, o in e.iterrows():
            if o.abnormal:
                if o.id not in visited_files:
                    if o.id == first_entry.id:
                        e.loc[_, 'abnormal'] = False
                    else:
                        if o.first_cluster < first_entry.first_cluster:
                            e.loc[_, 'deduced_time'] = '%s之前' %\
                                                       first_entry.create_time

                            visited_files.add(o.id)

        for _, o in e.iterrows():
            if o.abnormal:
                if o.id not in visited_files:
                    if o.id == last_entry.id:
                        e.loc[_, 'abnormal'] = False
                    else:
                        if last_entry.first_cluster <= o.first_cluster:
                            e.loc[_, 'deduced_time'] = '%s之后' % \
                                                       last_entry.create_time

                            visited_files.add(o.id)

        class ItIsSimplyNotPossible(BaseException):
            pass

        for _, o in e.iterrows():
            if o.abnormal:
                if o.id not in visited_files:
                    closest_entry_right = last_entry
                    for entry in reversed_entries_list:
                        if entry.id == o.id:
                            continue
                        if entry.first_cluster <= o.first_cluster:
                            closest_entry_left = entry
                            break
                        elif entry.first_cluster >= o.first_cluster:
                            closest_entry_right = entry
                    else:
                        raise ItIsSimplyNotPossible

                    e.loc[_, 'deduced_time'] = '%s与%s之间' % (
                        closest_entry_left.create_time,
                        closest_entry_right.create_time
                    )

                    visited_files.add(o.id)

        return e

    def add_figure(self, figure, label='绘图结果'):
        idx = self.figures_widget.addTab(FigureWidget(self, figure),
                                         label)
        self.figures_widget.setCurrentIndex(idx)

    def _show_timeline(self, start_time_attr, display_abnormal_source=True):
        conclusions = set()
        for _, row in self.entries.iterrows():
            for c in row.conclusions:
                conclusions.add(c)

        conclusions = list(conclusions)
        conclusions.append('无可用结论')

        groups, c_id = [], {}
        for i, c in enumerate(conclusions):
            groups.append({'id': i, 'content': c})
            c_id[c] = i

        def _gen_item(item, group_id=len(conclusions) - 1):
            content = '#%s' % item.id
            if display_abnormal_source:
                if item.abnormal_src:
                    content += '<br />%s' % ', '.join(item.abnormal_src)

            _ = {'start': item[start_time_attr].timestamp() * 1000,
                 'content': content,
                 'group': group_id}

            if item.abnormal:
                _['className'] = 'red'

            return _

        items = []
        for i, (_t, item) in enumerate(self.entries.iterrows()):
            if item.conclusions:
                for c in item.conclusions:
                    _ = _gen_item(item, c_id[c])
                    items.append(_)
            else:
                _ = _gen_item(item)
                items.append(_)


        html = self.timeline_template.render(
            groups=groups,
            items=items,
            start=self.summary_widget.start_time.timestamp() * 1000,
            end=self.summary_widget.end_time.timestamp() * 1000
        )

        if self.USE_QT_WEBKIT:
            view = QWebView(self)
            view.setHtml(html, self.timeline_base_url)
            self.figures_widget.addTab(view, '时间线')
        else:
            info_box(self, '将会打开外部浏览器查看时间线')

            path = os.path.join(self.template_path, 'r.html')
            print(html, file=open(path, 'w', encoding='utf-8'))
            webbrowser.open(QUrl.fromLocalFile(path).toString())

    def closeEvent(self, event):
        self.partition.stream.close()

        event.accept()
